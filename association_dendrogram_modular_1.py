import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import argparse
import os
import tkinter as tk
from tkinter import filedialog
import matplotlib

# Sett backend til interaktiv visning
matplotlib.use('TkAgg')

# ===== KONSTANTER FOR TILPASNING =====

# Figurstørrelse
FIGSIZE = (16, 12)  # Størrelse på figuren i tommer (bredde, høyde)

# Bakgrunnsfarge
BACKGROUND_COLOR = '#FFFFFF'  # Hvit bakgrunn

# Startvinkel for første assosiasjon (i grader)
START_ANGLE_DEGREES = 85  # Endret fra 5 til 85 grader

# Mellomrom mellom grupper som en andel av en assosiasjonsplass
SPACING_FACTOR = 0.5  # Mellomrom tilsvarende 50% av plassen til én assosiasjon

# Fargepalett for assosiasjoner
COLOR_PALETTE = [
    "#1C7CA1",  # Blue 
    "#F26649",  # Orange 
    "#2E6C60",  # Darkest_Aqua 
    "#F7A392",  # Light_orange 
    "#AADBD1",  # Light_Aqua 
    "#FCE164",  # Yellow 
    "#DD3310",  # Dark_orange 
    "#71C3B4",  # Aqua 
    "#0E3E51",  # Dark_blue 
    "#A08CC3",  # Purple 
    "#92D3EC",  # Light_blue 
    "#D2C309",  # Dark_Lt_yellow 
    "#525350",  # Dk_grey 
]

# Farger og størrelser for sirkler
CENTER_CIRCLE_COLOR = '#87CEFA'  # Lyseblå bakgrunn for sentrum
CENTER_CIRCLE_ALPHA = 0.7        # Gjennomsiktighet for sentrum-sirkel
PRIMARY_CIRCLE_SIZE = 0.018      # Størrelse på primærassosiasjons-sirkler
SECONDARY_CIRCLE_SIZE = 0.012    # Størrelse på sekundærassosiasjons-sirkler
CIRCLE_OUTLINE_COLOR = '#FFFFFF' # Hvit farge på de store sirklene som markerer nivåer

# Fontstørrelser
CENTER_FONT_SIZE = 40            # Fontstørrelse for sentrum-tekst
PRIMARY_FONT_SIZE = 14           # Fontstørrelse for primærassosiasjoner
SECONDARY_FONT_SIZE = 13         # Fontstørrelse for sekundærassosiasjoner

# Radier for de forskjellige nivåene
CENTER_RADIUS = 0.15             # Radius for sentrum-sirkel
PRIMARY_RADIUS = 0.45            # Radius for primærassosiasjoner
SECONDARY_RADIUS = 0.85          # Radius for sekundærassosiasjoner

# Linjestiler
PRIMARY_LINE_WIDTH = 0.8         # Linjetykkelse for primærlinjer
SECONDARY_LINE_WIDTH = 0.5       # Linjetykkelse for sekundærlinjer
LINE_ALPHA = 0.6                 # Gjennomsiktighet for linjer

# Tekstfarger
PRIMARY_TEXT_COLOR = '#333333'   # Farge på primærassosiasjonstekst
SECONDARY_TEXT_COLOR = '#555555' # Farge på sekundærassosiasjonstekst

# Tekstplassering
TEXT_OFFSET = 0.03               # Avstand fra sirkel til tekst

# ===== INNLESING AV DATA =====

def load_association_data(excel_file=None):
    """
    Leser inn assosiasjonsdataene fra en Excel-fil og returnerer en DataFrame.

    Parameters:
    -----------
    excel_file : str, optional
        Filsti til Excel-filen som inneholder assosiasjonsdataene.
        Første kolonne er primærassosiasjoner, påfølgende kolonner er sekundærassosiasjoner.
        Hvis None, vil en filvelger-dialog åpnes.

    Returns:
    --------
    pandas.DataFrame
        DataFrame med assosiasjonsdataene, der index er primærassosiasjoner
        og kolonnene er sekundærassosiasjoner.
    """
    if excel_file is None:
        root = tk.Tk()
        root.withdraw()
        excel_file = filedialog.askopenfilename(
            title="Velg Excel-fil med assosiasjonsdata",
            filetypes=[("Excel-filer", "*.xlsx *.xls"), ("Alle filer", "*.*")]
        )
        if not excel_file:
            print("Ingen fil valgt. Avslutter.")
            return None
        print(f"Valgt fil: {excel_file}")

    try:
        df = pd.read_excel(excel_file)

        if len(df.columns) < 2:
            print("Feil: Excel-filen må ha minst to kolonner: én for primærassosiasjoner og minst én for sekundærassosiasjoner.")
            return None

        primary_col = df.columns[0]
        df = df.dropna(subset=[primary_col])

        # Håndter duplikater i primærassosiasjoner
        value_counts = df[primary_col].value_counts()
        duplicates_mask = df[primary_col].map(value_counts) > 1
        if duplicates_mask.any():
            print("Advarsel: Det finnes duplikater i primærassosiasjonene. Legger til unike suffiks.")
            counts = df.groupby(primary_col).cumcount() + 1
            df[primary_col] = df.apply(
                lambda row: f"{row[primary_col]} ({counts[row.name]})" if duplicates_mask[row.name] else row[primary_col],
                axis=1
            )

        df = df.set_index(primary_col)

        print("\n=== INNLESTE ASSOSIASJONSDATA ===")
        print(df.to_string())
        print(f"\nAntall primærassosiasjoner: {len(df)}")
        print(f"Kolonner: {list(df.columns)}")

        return df

    except Exception as e:
        print(f"Feil ved lesing av data: {str(e)}")
        return None


# ===== VISUALISERING =====

def create_visualization(df, title_text=None):
    """
    Lager visualiseringen basert på dataframe.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Dataframe med assosiasjonsdataene, der index er primærassosiasjoner
    title_text : str, optional
        Teksten som skal vises i sentrum av visualiseringen. 
        Hvis None, vil brukeren bli spurt om å angi tekst.
    """
    if df is None:
        print("Ingen data å visualisere.")
        return
    
    # Spør brukeren om tekst i midten hvis ikke spesifisert
    if title_text is None:
        title_text = input("Skriv inn tekst som skal vises i midten (trykk Enter for tom tekst): ") or ""
    
    # Tildeler farger til primærassosiasjonene (gjentar farger om nødvendig)
    num_primary = len(df)
    primary_colors = [COLOR_PALETTE[i % len(COLOR_PALETTE)] for i in range(num_primary)]
    
    # Teller sekundærassosiasjoner og beregner effektive antall
    secondary_counts = []
    effective_counts = []
    
    for i, (primary, row) in enumerate(df.iterrows()):
        # Teller antall ikke-tomme sekundærassosiasjoner for hver rad
        count = sum(1 for val in row if pd.notna(val) and val != "")
        secondary_counts.append(count)
        # Behandler primærassosiasjoner uten sekundærassosiasjoner som om de har én
        effective_counts.append(max(1, count))
    
    # Oppretter figur med spesifisert bakgrunnsfarge og størrelse
    fig = plt.figure(figsize=FIGSIZE, facecolor=BACKGROUND_COLOR)
    ax = fig.add_subplot(111) 
    ax.set_facecolor(BACKGROUND_COLOR)
    ax.set_aspect('equal')
    ax.axis('off')  # Skjuler aksene

    # Konverterer polare koordinater til kartesiske
    def pol2cart(radius, angle):
        return radius * np.cos(angle), radius * np.sin(angle)

    # Funksjon for å beregne tekstrotasjon som sikrer at teksten alltid er lesbar (ikke opp-ned)
    def get_text_rotation(angle):
        # Konverterer til grader
        degrees = np.degrees(angle) % 360
        
        # Justerer rotasjonen for å unngå opp-ned tekst
        if 90 < degrees < 270:
            return degrees - 180
        else:
            return degrees

    # Beregner total antall effektive sekundærassosiasjoner
    total_effective_count = sum(effective_counts)
    
    # Beregner total vinkel som trengs for mellomrom
    total_spacing_angle = 2 * np.pi * SPACING_FACTOR * len(df) / total_effective_count
    
    # Beregner vinkel per effektiv sekundærassosiasjon
    angle_per_secondary = (2 * np.pi - total_spacing_angle) / total_effective_count
    
    # Konverterer startvinkel fra grader til radianer
    start_angle_rad = np.radians(START_ANGLE_DEGREES)
    
    # Fordeler gruppene rundt hele sirkelen med klokka, startende fra startvinkel
    primary_angles = []
    secondary_angles = {}
    
    current_angle = start_angle_rad
    
    for i in range(num_primary):
        num_secondaries = secondary_counts[i]
        effective_count = effective_counts[i]
        
        # Beregner total vinkel for denne gruppen
        group_angle = effective_count * angle_per_secondary
        
        # Beregner mellomrom mellom sekundærassosiasjoner innenfor gruppen
        if num_secondaries > 0:
            # Fordeler sekundærassosiasjoner jevnt innenfor gruppens vinkel
            sec_angle = group_angle / num_secondaries
            
            # Plasserer primærassosiasjonen i midten av gruppen
            primary_angle = current_angle - group_angle / 2
            primary_angles.append(primary_angle)
            
            # Plasserer sekundærassosiasjoner
            secondary_angles[i] = []
            for j in range(num_secondaries):
                # Beregner vinkel for hver sekundærassosiasjon
                sec_pos = current_angle - (j + 0.5) * sec_angle
                secondary_angles[i].append(sec_pos)
        else:
            # Hvis ingen sekundærassosiasjoner, plasserer primær i midten av sin tildelte plass
            primary_angle = current_angle - group_angle / 2
            primary_angles.append(primary_angle)
        
        # Legger til mellomrom etter hver gruppe
        group_spacing = angle_per_secondary * SPACING_FACTOR
        
        # Oppdaterer vinkel for neste gruppe
        current_angle -= (group_angle + group_spacing)
    
    # Tegner sentrum med sentrum-tekst
    ax.add_patch(plt.Circle((0, 0), CENTER_RADIUS, color=CENTER_CIRCLE_COLOR, alpha=CENTER_CIRCLE_ALPHA, zorder=10))
    ax.text(0, 0, title_text, ha='center', va='center', fontsize=CENTER_FONT_SIZE, fontweight='bold', color='black', zorder=11)

    # Tegner primærassosiasjoner og deres forbindelser
    for i, (primary, row) in enumerate(df.iterrows()):
        angle = primary_angles[i]
        x, y = pol2cart(PRIMARY_RADIUS, angle)
        
        # Henter farge for denne primærassosiasjonen
        color = primary_colors[i]
        
        # Tegner linje fra sentrum til primærassosiasjon
        ax.plot([0, x], [0, y], color=color, alpha=LINE_ALPHA, linewidth=PRIMARY_LINE_WIDTH, zorder=1)
        
        # Tegner primærassosiasjonspunkt med fargen fra paletten
        ax.add_patch(plt.Circle((x, y), PRIMARY_CIRCLE_SIZE, color=color, alpha=0.9, zorder=5))
        
        # Beregner tekstplassering for primærassosiasjon
        degrees = np.degrees(angle) % 360
        
        # Justerer tekstplassering basert på vinkel
        if 90 < degrees < 270:  # Venstre side
            ha = 'right'  # Høyrejusterer teksten på venstre side
        else:  # Høyre side
            ha = 'left'
        
        text_radius = PRIMARY_RADIUS + TEXT_OFFSET
        
        text_x, text_y = pol2cart(text_radius, angle)
        
        # Beregner rotasjon for radielt orientert tekst (men ikke opp-ned)
        rotation = get_text_rotation(angle)
        
        # Midtjusterer teksten radielt i forhold til markøren
        va = 'center'  # Alltid midtjustert vertikalt
        
        ax.text(text_x, text_y, primary, ha=ha, va=va, fontsize=PRIMARY_FONT_SIZE,
                rotation=rotation, rotation_mode='anchor', 
                fontweight='bold', zorder=6, color=PRIMARY_TEXT_COLOR)
        
        # Samler sekundærassosiasjoner fra raden (nå enklere!)
        secondaries = [val for val in row if pd.notna(val) and val != ""]
        
        # Tegner sekundærassosiasjoner
        if secondaries and i in secondary_angles:
            for j, (secondary, sec_angle) in enumerate(zip(secondaries, secondary_angles[i])):
                # Beregner posisjon for sekundærassosiasjon
                sec_x, sec_y = pol2cart(SECONDARY_RADIUS, sec_angle)
                
                # Tegner linje fra primær til sekundær med samme farge som primærassosiasjonen
                ax.plot([x, sec_x], [y, sec_y], color=color, alpha=LINE_ALPHA, linewidth=SECONDARY_LINE_WIDTH, zorder=1)
                
                # Tegner sekundærassosiasjonspunkt med samme farge som primærassosiasjonen
                ax.add_patch(plt.Circle((sec_x, sec_y), SECONDARY_CIRCLE_SIZE, color=color, alpha=0.7, zorder=4))
                
                # Beregner tekstplassering for sekundærassosiasjon
                sec_degrees = np.degrees(sec_angle) % 360
                
                # Justerer tekstplassering basert på vinkel
                if 90 < sec_degrees < 270:  # Venstre side
                    sec_ha = 'right'  # Høyrejusterer teksten på venstre side
                else:  # Høyre side
                    sec_ha = 'left'
                
                sec_text_radius = SECONDARY_RADIUS + TEXT_OFFSET
                
                sec_text_x, sec_text_y = pol2cart(sec_text_radius, sec_angle)
                
                # Beregner rotasjon for radielt orientert tekst (men ikke opp-ned)
                sec_rotation = get_text_rotation(sec_angle)
                
                # Midtjusterer teksten radielt i forhold til markøren
                sec_va = 'center'  # Alltid midtjustert vertikalt
                
                ax.text(sec_text_x, sec_text_y, secondary, ha=sec_ha, va=sec_va, fontsize=SECONDARY_FONT_SIZE,
                       rotation=sec_rotation, rotation_mode='anchor', zorder=6, color=SECONDARY_TEXT_COLOR)

    # Tegner sirkler for å markere de forskjellige nivåene
    ax.add_patch(plt.Circle((0, 0), PRIMARY_RADIUS, fill=False, color=CIRCLE_OUTLINE_COLOR, linestyle='-', linewidth=0.5, zorder=2))
    ax.add_patch(plt.Circle((0, 0), SECONDARY_RADIUS, fill=False, color=CIRCLE_OUTLINE_COLOR, linestyle='-', linewidth=0.5, zorder=2))

    # Setter grenser for plottet med litt mer margin
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    # Justerer layout
    plt.tight_layout()
    
    # Vis figuren og hold den åpen til brukeren lukker den
    plt.show()

# ===== HOVEDFUNKSJON SOM KOMBINERER BEGGE =====

def create_association_dendrogram(excel_file=None, title_text=None):
    """
    Hovedfunksjon som kombinerer datainnlesing og visualisering.
    
    Parameters:
    -----------
    excel_file : str, optional
        Filsti til Excel-filen som inneholder assosiasjonsdataene.
        Hvis None, vil en filvelger-dialog åpnes.
    
    title_text : str, optional
        Teksten som skal vises i sentrum av visualiseringen. 
        Hvis None, vil brukeren bli spurt om å angi tekst.
    """
    # Last inn data
    df = load_association_data(excel_file)
    
    # Lag visualisering hvis data ble lastet inn
    if df is not None:
        create_visualization(df, title_text)
    else:
        print("Kunne ikke lage visualisering på grunn av problemer med datainnlesing.")

# ===== KOMMANDOLINJE-GRENSESNITT =====

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lag en visualisering av assosiasjoner fra en Excel-fil.')
    parser.add_argument('--data', help='Filsti til Excel-filen med assosiasjonsdata')
    parser.add_argument('--title', help='Tekst som skal vises i sentrum (standard: tom tekst)')
    
    args = parser.parse_args()
    
    create_association_dendrogram(args.data, args.title)
