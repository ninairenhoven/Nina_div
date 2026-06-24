import os
import pandas as pd

def write_dfs_to_excel(dfs: dict, filepath: str, engine: str = "xlsxwriter", auto_width: bool = True):
    """
    Lagre flere pandas DataFrames til hver sitt ark i én Excel-fil.
    #
    Parameters
    ----------
    dfs : dict[str, pd.DataFrame]
        Ordbok med {arknavn: dataframe}
    filepath : str
        Filsti til Excel-fil (f.eks. 'output/rapport.xlsx')
    engine : str
        Excel-writer engine ('xlsxwriter' eller 'openpyxl')
    auto_width : bool
        Hvis True, juster kolonnebredde basert på innhold
    """
    print(filepath)
    # Sørg for at mappe finnes
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    #
    with pd.ExcelWriter(filepath, engine=engine) as writer:
        for sheet_name, df in dfs.items():
            print(sheet_name)
            # Skriv DF til ark
            df.to_excel(writer, sheet_name=sheet_name, index=True)
            #
            if auto_width:
                # Hent workbook/worksheet for breddejustering (krever xlsxwriter)
                if engine == "xlsxwriter":
                    worksheet = writer.sheets[sheet_name]
                    # Estimer maksimal bredde per kolonne
                    for i, col in enumerate(df.columns):
                        # Max lengde av kolonnen eller header
                        max_len = max(
                            [len(str(col))] + [len(str(v)) for v in df[col].astype(str).values]
                        )
                        # Litt padding
                        worksheet.set_column(i, i, max_len + 2)
    #
    print(f"Skrev {len(dfs)} ark til: {filepath}")

