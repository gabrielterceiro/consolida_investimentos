import pandas as pd
import os
from datetime import datetime
import warnings
import configparser
import yfinance as yf
import xlsxwriter # Required for formatting, though pd.ExcelWriter handles the writing

# docker build -t consolidador-investimentos .

# Ignore the specific UserWarning from openpyxl related to data validation
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# --- Configuration Loading ---
def load_config(config_file="input/config/config.ini"):
    """
    Loads configuration from config.ini. Creates a default if it doesn't exist.
    """
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        print(f"Configuration file '{config_file}' not found. Creating a default...")
        config['Paths'] = {
            'InputFolder': 'input',
            'OutputFolder': 'output',
            'CorrectionsFolder': 'input/correcoes'
        }
        config['Settings'] = {
            'CutoffDate': '2025-12-31' # YYYY-MM-DD format
        }
        os.makedirs(os.path.dirname(config_file), exist_ok=True) # Ensure directory exists
        with open(config_file, 'w') as f:
            config.write(f)
        print(f"Default configuration file created at '{config_file}'. Please review and adjust settings if necessary.")
    
    config.read(config_file)
    return config

# --- Function to read all transaction data from the input folder ---
def load_transactions_from_folder(folder_path):
    """
    Loads all 'Movimentação' sheets from .xlsx files in the specified folder.
    """
    if not os.path.exists(folder_path):
        print(f"WARNING: Input folder '{folder_path}' not found. Please create it and place your Excel statement files there.")
        return pd.DataFrame() # Return empty DataFrame if folder doesn't exist

    excel_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".xlsx")]
    if not excel_files:
        print(f"WARNING: No .xlsx files found in folder '{folder_path}'. Please place your statements here.")
        return pd.DataFrame()

    all_transactions_df = pd.DataFrame()
    for file_path in excel_files:
        print(f"Reading file: {file_path}")
        try:
            df = pd.read_excel(file_path, sheet_name="Movimentação", engine="openpyxl")
            # Ensure 'Data' and 'Preço unitário' columns exist before processing
            if "Data" not in df.columns or "Preço unitário" not in df.columns:
                print(f"WARNING: File '{file_path}' does not contain 'Data' or 'Preço unitário' columns in the 'Movimentação' sheet. Skipping this file.")
                continue

            df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
            df["Preço unitário"] = pd.to_numeric(df["Preço unitário"], errors="coerce")
            all_transactions_df = pd.concat([all_transactions_df, df], ignore_index=True)
        except KeyError:
            print(f"WARNING: File '{file_path}' does not have the 'Movimentação' sheet. Skipping this file.")
        except Exception as e:
            print(f"ERROR reading file {file_path}: {e}. Skipping this file.")
    return all_transactions_df

# --- Function to load stock splits/groupings ---
def load_splits_and_groupings(file_path):
    """
    Loads stock splits/groupings from the specified Excel file.
    """
    if not os.path.exists(file_path):
        print(f"WARNING: Splits/groupings file '{file_path}' not found. Check the corrections folder.")
        return pd.DataFrame()
    print(f"Reading splits/groupings file: {file_path}")
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        # Ensure required columns exist
        if not all(col in df.columns for col in ["Ticker", "Fator", "Data"]):
            print(f"WARNING: File '{file_path}' does not contain all required columns (Ticker, Fator, Data). Skipping splits/groupings.")
            return pd.DataFrame()
            
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
        return df
    except Exception as e:
        print(f"ERROR loading splits/groupings file '{file_path}': {e}. Splits/groupings will not be applied.")
        return pd.DataFrame()

# --- Apply splits/groupings to transactions up to the cutoff date ---
def apply_splits_and_groupings(transactions_df, cutoff_date, splits_df):
    """
    Applies stock splits/groupings to transactions based on their date and the cutoff date.
    """
    if splits_df.empty or transactions_df.empty:
        if not transactions_df.empty: # Only print if there were transactions to begin with
             print("No splits/groupings data to apply, or no transactions loaded.")
        return transactions_df

    print("Applying splits/groupings...")
    df_copy = transactions_df.copy() # Work on a copy to avoid SettingWithCopyWarning

    # Ensure date columns are datetime type for comparison
    df_copy["Data"] = pd.to_datetime(df_copy["Data"])
    splits_df["Data"] = pd.to_datetime(splits_df["Data"])
    cutoff_date_dt = pd.to_datetime(cutoff_date)

    for _, row in splits_df.iterrows():
        ticker, factor, split_date = row["Ticker"], row["Fator"], row["Data"]

        # Check if the split date is on or before the cutoff date
        if split_date <= cutoff_date_dt:
            # Filter transactions that match the ticker and occurred
            # on or before the split date.
            filter_condition = df_copy["Produto"].str.contains(ticker, na=False) & \
                                 (df_copy["Data"] <= split_date)

            # Apply the split factor to Quantity and Unit Price
            df_copy.loc[filter_condition, "Quantidade"] *= factor
            df_copy.loc[filter_condition, "Preço unitário"] /= factor
        else:
            print(f"Split/grouping for {ticker} on {split_date.strftime('%Y-%m-%d')} ignored (after cutoff date {cutoff_date_dt.strftime('%Y-%m-%d')}).")
    return df_copy

def apply_ticker_renames(transactions_df, renames_file_path):
    """
    Applies ticker renames from the specified Excel file.
    The 'Ticker' column in transactions_df is expected to exist.
    """
    print(f"Applying Ticker renames...")
    try:
        if not os.path.exists(renames_file_path):
            print(f"WARNING: Renames file '{renames_file_path}' not found. Skipping renames.")
            return transactions_df

        renames_df = pd.read_excel(renames_file_path, engine="openpyxl")
        if not all(col in renames_df.columns for col in ["Ticker Antigo", "Ticker Novo"]):
            print(f"WARNING: File '{renames_file_path}' does not contain 'Ticker Antigo' and 'Ticker Novo' columns. Skipping renames.")
            return transactions_df
            
        rename_map = dict(zip(renames_df["Ticker Antigo"], renames_df["Ticker Novo"]))
        
        # Ensure 'Ticker' column exists before trying to replace values in it
        if "Ticker" in transactions_df.columns:
            transactions_df["Ticker"] = transactions_df["Ticker"].replace(rename_map)
        else:
            print("WARNING: 'Ticker' column not found in transactions_df. Cannot apply renames.")
            
    except Exception as e:
        print(f"ERROR applying renames: {e}. Renames will not be applied.")
    return transactions_df

# --- Consolidate position up to a certain date ---
def consolidate_position(transactions_df, cutoff_date, renames_file_path):
    """
    Consolidates the investment position up to the cutoff date.
    Returns a DataFrame with columns: ["Ativo", "Quantidade", "Preço Médio", "Custo Total"]
    """
    print("Consolidating positions...")
    # Define Portuguese column names for the empty DataFrame case
    pt_columns_position = ["Ativo", "Quantidade", "Preço Médio", "Custo Total"]
    if transactions_df.empty:
        print("No transactions to consolidate position.")
        return pd.DataFrame(columns=pt_columns_position)

    df_filtered = transactions_df[transactions_df["Data"] <= pd.to_datetime(cutoff_date)].copy()

    valid_transaction_types = {
        "Compra": "Buy",
        "Venda": "Sell",
        "Transferência - Liquidação": "Transfer_Settlement",
        "Leilão de Fração": "Buy", 
        "Bonificação em Ativos": "Buy", 
        "Fração em Ativos": "Sell" 
    }

    df_filtered = df_filtered[df_filtered["Movimentação"].isin(valid_transaction_types.keys())].copy()

    if df_filtered.empty:
        print("No valid transactions after filtering to consolidate position.")
        return pd.DataFrame(columns=pt_columns_position)

    df_filtered["Type"] = df_filtered.apply(lambda row: (
        "Buy" if valid_transaction_types[row["Movimentação"]] == "Transfer_Settlement" and row["Entrada/Saída"] == "Credito"
        else "Sell" if valid_transaction_types[row["Movimentação"]] == "Transfer_Settlement" and row["Entrada/Saída"] == "Debito"
        else valid_transaction_types[row["Movimentação"]]
    ), axis=1)

    df_filtered["Quantidade"] = df_filtered["Quantidade"].fillna(0)
    df_filtered["Preço unitário"] = pd.to_numeric(df_filtered["Preço unitário"].fillna(0), errors='coerce') 
    df_filtered["Ticker"] = df_filtered["Produto"].str.extract(r"^([^\s-]+)")[0] # Extract ticker
    df_filtered = apply_ticker_renames(df_filtered, renames_file_path) # Apply renames on 'Ticker' column

    df_filtered["Adjusted Quantity"] = df_filtered.apply(
        lambda row: -row["Quantidade"] if row["Type"] == "Sell" else row["Quantidade"],
        axis=1
    )
    df_filtered["Cost"] = df_filtered.apply(
        lambda row: row["Quantidade"] * row["Preço unitário"] if row["Type"] == "Buy" else 0,
        axis=1
    )
    
    # Group by the 'Ticker' column which now contains potentially renamed tickers
    grouped_df = df_filtered.groupby("Ticker").agg({
        "Adjusted Quantity": "sum",
        "Cost": "sum"
    }).reset_index()

    # Rename columns to Portuguese
    grouped_df.columns = ["Ativo", "Quantidade", "Custo Total"] 
    grouped_df = grouped_df[grouped_df["Quantidade"] > 0].copy() 
    
    grouped_df["Preço Médio"] = grouped_df.apply(
        lambda row: row["Custo Total"] / row["Quantidade"] if row["Quantidade"] != 0 else 0,
        axis=1
    )

    return grouped_df[["Ativo", "Quantidade", "Preço Médio", "Custo Total"]]

# --- Generate portfolio tab ---
def get_current_price_yf(ticker):
    """
    Fetches the current price of a stock or FII using yfinance.
    Adds '.SA' to Brazilian tickers if not already present.
    """
    try:
        if not ticker.endswith('.SA') and not '.' in ticker: 
            ticker_sa = f"{ticker}.SA"
        else:
            ticker_sa = ticker

        stock_info = yf.Ticker(ticker_sa)
        current_price = stock_info.info.get('regularMarketPrice')
        if current_price is None:
            current_price = stock_info.info.get('currentPrice')
        
        if current_price is None:
             print(f"Could not fetch price for {ticker_sa}. Check ticker or API response.")
        return current_price
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None
    
def build_portfolio_view(position_df):
    """
    Adds current market value columns to the position DataFrame.
    Assumes position_df has columns: ["Ativo", "Quantidade", "Preço Médio", "Custo Total"]
    Returns DataFrame with columns: ["Ativo", "Quantidade", "Preço Médio", "Custo Total", "Valor Unit. Atual", "Valor Total Atual", "L/P"]
    """
    pt_columns_portfolio = ["Ativo", "Quantidade", "Preço Médio", "Custo Total", "Valor Unit. Atual", "Valor Total Atual", "L/P"]
    if position_df.empty:
        return pd.DataFrame(columns=pt_columns_portfolio)

    print("Fetching current prices for portfolio... This may take a few seconds.")
    df_portfolio = position_df.copy()

    # 'position_df' already has columns "Ativo", "Quantidade", "Preço Médio", "Custo Total"
    df_portfolio['Valor Unit. Atual'] = df_portfolio['Ativo'].apply(get_current_price_yf)
    
    df_portfolio['Valor Total Atual'] = df_portfolio.apply(
        lambda row: row['Quantidade'] * row['Valor Unit. Atual'] if pd.notnull(row['Valor Unit. Atual']) else None,
        axis=1
    )

    df_portfolio['L/P'] = df_portfolio['Valor Total Atual'].fillna(0) - df_portfolio['Custo Total'].fillna(0)
    
    # Reorder columns to ensure desired final order
    # All columns are already in Portuguese
    return df_portfolio[pt_columns_portfolio]

# --- Generate income tab ---
def consolidate_income(transactions_df):
    """
    Consolidates dividends, JCP (Interest on Own Capital), and other income.
    Returns DataFrame with columns: ["Ativo", "Ano", "Renda Total"]
    """
    print("Consolidating income...")
    pt_columns_income = ["Ativo", "Ano", "Renda Total"]
    if transactions_df.empty:
        print("No transactions to consolidate income.")
        return pd.DataFrame(columns=pt_columns_income)

    income_types = ["Dividendo", "Juros Sobre Capital Próprio", "Rendimento"]
    df_income = transactions_df[transactions_df["Movimentação"].isin(income_types)].copy()
    df_income["Valor da Operação"] = pd.to_numeric(df_income["Valor da Operação"], errors="coerce")
    df_income = df_income.dropna(subset=["Valor da Operação"]).copy()

    if df_income.empty:
        print("No valid income entries found.")
        return pd.DataFrame(columns=pt_columns_income)

    df_income["Ticker"] = df_income["Produto"].str.extract(r"^([^\s-]+)")[0] # Extract Ticker from Produto
    df_income["Ano"] = df_income["Data"].dt.year

    result_df = df_income.groupby(["Ticker", "Ano"])["Valor da Operação"].sum().reset_index()
    result_df.columns = pt_columns_income # Rename to Portuguese
    return result_df

# --- Generate sales tab ---
def consolidate_sales(transactions_df):
    """
    Consolidates sales transactions.
    Returns DataFrame with columns: ["Data", "Produto", "Quantidade", "Preço unitário", "Valor da Operação"]
    """
    print("Consolidating sales...")
    pt_columns_sales = ["Data", "Produto", "Quantidade", "Preço unitário", "Valor da Operação"]
    if transactions_df.empty:
        print("No transactions to consolidate sales.")
        return pd.DataFrame(columns=pt_columns_sales)

    df_sales = transactions_df[
        (transactions_df["Movimentação"] == "Venda") | 
        ((transactions_df["Movimentação"] == "Transferência - Liquidação") & (transactions_df["Entrada/Saída"] == "Debito"))
    ].copy()
    
    if df_sales.empty:
        print("No sales transactions found after filtering.")
        return pd.DataFrame(columns=pt_columns_sales)

    if "Quantidade" in df_sales.columns:
        df_sales["Quantidade"] = pd.to_numeric(df_sales["Quantidade"], errors='coerce')
    if "Preço unitário" in df_sales.columns:
        df_sales["Preço unitário"] = pd.to_numeric(df_sales["Preço unitário"], errors='coerce')
    if "Valor da Operação" in df_sales.columns:
        df_sales["Valor da Operação"] = pd.to_numeric(df_sales["Valor da Operação"], errors='coerce')
    
    return df_sales[pt_columns_sales] # Columns are already in Portuguese

# --- Generate final Excel output ---
def generate_output_excel(portfolio_df, position_df, sales_df, income_df, output_path):
    """
    Generates the final Excel output file with four sheets and applies currency formatting.
    """
    print(f"Generating output file: {output_path}")
    try:
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            
            sheets_data = {
                "Portfolio": portfolio_df,
                "Posicao_Custo": position_df, 
                "Vendas_Log": sales_df,       
                "Rendimentos_Log": income_df  
            }

            for sheet_name, df_to_write in sheets_data.items():
                if df_to_write is not None and not df_to_write.empty:
                    df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)

            workbook = writer.book
            money_format = workbook.add_format({'num_format': 'R$ #,##0.00'}) 

            # Define which columns need currency format for each sheet
            # Ensures that the formatting is applied correctly with Portuguese column names
            currency_columns_map = {
                "Portfolio": ['Preço Médio', 'Custo Total', 'Valor Unit. Atual', 'Valor Total Atual', 'L/P'],
                "Posicao_Custo": ['Preço Médio', 'Custo Total'],
                "Vendas_Log": ['Preço unitário', 'Valor da Operação'],
                "Rendimentos_Log": ['Renda Total']
            }
            
            # Auto-adjust column widths and apply formats in a single loop
            # This prevents the width adjustment from overriding the cell format
            for sheet_name, df_data in sheets_data.items():
                if sheet_name in writer.sheets: 
                    worksheet = writer.sheets[sheet_name]
                    if df_data is not None and not df_data.empty:
                        # Get the list of currency columns for the current sheet
                        sheet_currency_columns = currency_columns_map.get(sheet_name, [])

                        for idx, col_name in enumerate(df_data.columns): # col_name is the actual column name from DataFrame
                            series = df_data[col_name]
                            # Calculate max length for column width
                            max_data_len = series.astype(str).map(len).max() if not series.empty else 0
                            header_len = len(str(col_name))
                            max_len = max(max_data_len, header_len) + 2  
                            
                            current_format_to_apply = None
                            if col_name in sheet_currency_columns:
                                current_format_to_apply = money_format
                            
                            # Apply width and format together
                            worksheet.set_column(idx, idx, max_len, current_format_to_apply)
                    else: 
                        # Default width for an empty sheet's first column if sheet was created empty
                        worksheet.set_column(0, 0, 20) 

        print("\nSUCCESS: Output file generated successfully!")
    except Exception as e:
        print(f"CRITICAL ERROR generating output file '{output_path}': {e}")
        import traceback
        traceback.print_exc()

# --- Main execution block ---
if __name__ == "__main__":
    print("Starting Investment Consolidator...")
    
    config = load_config()
    
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    
    input_folder = os.path.join(base_dir, config['Paths']['InputFolder'])
    output_folder = os.path.join(base_dir, config['Paths']['OutputFolder'])
    corrections_folder = os.path.join(base_dir, config['Paths']['CorrectionsFolder'])
    
    splits_file_path = os.path.join(corrections_folder, "desdobramentos.xlsx") 
    renames_file_path = os.path.join(corrections_folder, "renomeacoes.xlsx") 
    output_file_path = os.path.join(output_folder, "consolidated_investments.xlsx")

    os.makedirs(input_folder, exist_ok=True) 
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(corrections_folder, exist_ok=True)

    try:
        cutoff_date_str = config['Settings']['CutoffDate']
        cutoff_date = datetime.strptime(cutoff_date_str, '%Y-%m-%d')
    except ValueError:
        print(f"ERROR: Cutoff date in config.ini '{cutoff_date_str}' has an invalid format. Use YYYY-MM-DD. Using 2025-12-31 as default.")
        cutoff_date = datetime(2025, 12, 31)

    print(f"\nSettings:")
    print(f"  Cutoff date set to: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"  Transaction statements folder (input): '{input_folder}'")
    print(f"  Corrections folder (splits, renames): '{corrections_folder}'")
    print(f"  Output file: '{output_file_path}'")
    print("-" * 50)

    try:
        all_transactions_df = load_transactions_from_folder(input_folder)
        
        if all_transactions_df.empty:
            print("\nNo transaction data to process. Please place your .xlsx files in the 'input' folder.")
        else:
            splits_df = load_splits_and_groupings(splits_file_path)
            
            processed_transactions_df = apply_splits_and_groupings(all_transactions_df.copy(), cutoff_date, splits_df)

            position_cost_basis_df = consolidate_position(processed_transactions_df.copy(), cutoff_date, renames_file_path)
            
            sales_log_df = consolidate_sales(processed_transactions_df.copy())
            income_log_df = consolidate_income(processed_transactions_df.copy())
            
            portfolio_market_view_df = build_portfolio_view(position_cost_basis_df.copy()) 

            generate_output_excel(portfolio_market_view_df, position_cost_basis_df, sales_log_df, income_log_df, output_file_path)
            
    except Exception as e:
        print(f"\nAN UNEXPECTED ERROR OCCURRED DURING PROCESSING: {e}")
        import traceback
        traceback.print_exc()
