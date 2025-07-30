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
FIGSIZE = (14, 10)  # Størrelse på figuren i tommer (bredde, høyde)

# Bakgrunnsfarge
BACKGROUND_COLOR = '#FFFFFF'  

# Startvinkel for første assosiasjon (i grader)
START_ANGLE_DEGREES = 85  

# Mellomrom mellom grupper som en andel av en assosiasjonsplass
SPACING_FACTOR = 0.5  # Mellomrom tilsvarende 50% av plassen til én assosiasjon

# Fontstørrelser
CENTER_FONT_SIZE = 18            # Fontstørrelse for sentrum-tekst
LEVEL_FONT_SIZES = [10, 9, 9, 9]  # Fontstørrelser for nivå 1-4

# Radier for de forskjellige nivåene
CENTER_RADIUS = 0.1             # Radius for sentrum-sirkel
LEVEL_RADII = [0.20, 0.5, 0.85, 1.05]  # Radier for nivå 1-4

# Linjestiler
LEVEL_LINE_WIDTHS = [1, 0.8, 0.7, 0.6]  # Linjetykkelser for nivå 1-4
LINE_ALPHA = 0.3                 # Gjennomsiktighet for linjer (0 = usynlig linje)

# Tekstfarger
LEVEL_TEXT_COLORS = ['#333333', '#444444', '#555555', '#666666']  # Farger for nivå 1-4

# Maksimal tekstlengde per nivå før teksten brytes i to linjer
LEVEL_MAX_TEXT_LENGTHS = [12, 100, 100, 100]  # Nivå 1-4

# Tekstplassering
TEXT_OFFSET = 0.03               # Avstand fra sirkel til tekst

# Farger og størrelser for sirkler
CENTER_CIRCLE_COLOR = '#87CEFA'  # Lyseblå bakgrunn for sentrum
CENTER_CIRCLE_ALPHA = 0.7        # Gjennomsiktighet for sentrum-sirkel
LEVEL_CIRCLE_SIZES = [0.018, 0.015, 0.012, 0.010]  # Størrelser for nivå 1-4
CIRCLE_OUTLINE_COLOR = '#FFFFFF' # Hvit farge på de store sirklene som markerer nivåer

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




# ===== INNLESING AV DATA =====

def load_association_data(excel_file=None):
    """
    Leser inn assosiasjonsdataene fra en Excel-fil og returnerer en strukturert dataramme.
    
    Parameters:
    -----------
    excel_file : str, optional
        Filsti til Excel-filen som inneholder assosiasjonsdataene.
        Hvis None, vil en filvelger-dialog åpnes.
        
    Returns:
    --------
    dict
        En dictionary med hierarkisk struktur av assosiasjoner.
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
        # Les inn Excel-filen
        df = pd.read_excel(excel_file)
        
        # Fjern tomme kolonner og rader
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        # Sjekk at vi har minst to kolonner
        if len(df.columns) < 2:
            print("Feil: Excel-filen må ha minst to kolonner for assosiasjoner.")
            return None
        
        # Gi kolonner standardnavn hvis de ikke har navn
        for i in range(len(df.columns)):
            if pd.isna(df.columns[i]) or df.columns[i] == '' or 'Unnamed' in str(df.columns[i]):
                df.columns.values[i] = f"Nivå {i+1}"
        
        # Fjern rader der første kolonne er tom
        df = df.dropna(subset=[df.columns[0]])
        
        # Bygg hierarkisk struktur
        hierarchy = build_association_hierarchy(df)
        
        print("\n=== INNLESTE ASSOSIASJONSDATA ===")
        print(f"Antall primærassosiasjoner: {len(hierarchy)}")
        print(f"Kolonner (nivåer): {list(df.columns)}")
        
        return hierarchy, df.columns.tolist()

    except Exception as e:
        print(f"Feil ved lesing av data: {str(e)}")
        return None, None

def build_association_hierarchy(df):
    """
    Bygger en hierarkisk struktur av assosiasjoner fra datarammen.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Dataramme med assosiasjonsdata.
        
    Returns:
    --------
    dict
        En dictionary med hierarkisk struktur av assosiasjoner.
    """
    hierarchy = {}
    
    # Gå gjennom hver rad i datarammen
    for _, row in df.iterrows():
        current_level = hierarchy
        parent_key = None
        parent_dict = None
        
        # Gå gjennom hver kolonne (nivå) i raden
        for i, col in enumerate(df.columns):
            value = row[col]
            
            # Hopp over tomme verdier
            if pd.isna(value) or value == '':
                break
                
            # For første nivå (primærassosiasjoner)
            if i == 0:
                if value not in hierarchy:
                    hierarchy[value] = {'children': {}}
                current_level = hierarchy[value]['children']
                parent_key = value
                parent_dict = hierarchy
            # For påfølgende nivåer
            else:
                if parent_key is not None:
                    if value not in current_level:
                        current_level[value] = {'children': {}}
                    parent_dict = current_level
                    current_level = current_level[value]['children']
                    parent_key = value
    
    return hierarchy

# ===== VINKLER OG POSISJONERING =====

def calculate_positions(hierarchy, max_levels=4):
    """
    Beregner posisjoner for alle assosiasjoner i hierarkiet.
    
    Parameters:
    -----------
    hierarchy : dict
        Hierarkisk struktur av assosiasjoner.
    max_levels : int, optional
        Maksimalt antall nivåer å vise.
        
    Returns:
    --------
    dict
        Dictionary med posisjoner for alle assosiasjoner.
    """
    positions = {'center': (0, 0)}
    
    # Tell antall noder på hvert nivå for å beregne vinkler
    total_nodes = count_nodes_by_level(hierarchy, max_levels)
    
    # Beregn total vinkel for hele sirkelen
    total_angle = 2 * np.pi
    
    # Startvinkel (konverter fra grader til radianer)
    start_angle = np.radians(START_ANGLE_DEGREES)
    
    # Beregn posisjoner for primærassosiasjoner (nivå 1)
    level1_keys = list(hierarchy.keys())
    level1_count = len(level1_keys)
    
    # Beregn effektivt antall noder for vinkelfordeling
    effective_count = sum(count_children(hierarchy[key], max_levels-1) + 1 for key in level1_keys)
    angle_per_node = total_angle / (effective_count + level1_count * SPACING_FACTOR)
    
    current_angle = start_angle
    
    # Fordel primærassosiasjoner rundt sirkelen
    for i, key in enumerate(level1_keys):
        # Beregn antall barn for denne primærassosiasjonen
        children_count = count_children(hierarchy[key], max_levels-1)
        effective_space = (children_count + 1) * angle_per_node
        
        # Plasser primærassosiasjonen i midten av sin tildelte plass
        node_angle = current_angle - effective_space / 2
        x, y = pol2cart(LEVEL_RADII[0], node_angle)
        positions[key] = (x, y, node_angle)
        
        # Beregn posisjoner for barn rekursivt
        if 'children' in hierarchy[key] and len(hierarchy[key]['children']) > 0:
            calculate_child_positions(
                hierarchy[key]['children'], 
                positions, 
                key, 
                (x, y), 
                node_angle,
                current_angle - effective_space,
                current_angle,
                1,
                max_levels,
                angle_per_node
            )
        
        # Oppdater vinkel for neste primærassosiasjon
        current_angle -= effective_space
        
        # Legg til mellomrom mellom grupper
        if i < level1_count - 1:
            current_angle -= angle_per_node * SPACING_FACTOR
    
    return positions

def calculate_child_positions(children_dict, positions, parent_key, parent_pos, parent_angle, 
                             start_angle, end_angle, current_level, max_levels, angle_per_node):
    """
    Beregner posisjoner for barn rekursivt.
    
    Parameters:
    -----------
    children_dict : dict
        Dictionary med barn.
    positions : dict
        Dictionary med posisjoner som skal oppdateres.
    parent_key : str
        Nøkkel for foreldrenoden.
    parent_pos : tuple
        Posisjon for foreldrenoden (x, y).
    parent_angle : float
        Vinkel for foreldrenoden.
    start_angle : float
        Startvinkel for barnas område.
    end_angle : float
        Sluttvinkel for barnas område.
    current_level : int
        Gjeldende nivå (0-basert).
    max_levels : int
        Maksimalt antall nivåer.
    angle_per_node : float
        Vinkel per node.
    """
    # Stopp rekursjon hvis vi har nådd maksimalt nivå
    if current_level >= max_levels:
        return
    
    # Hent barn
    children = list(children_dict.keys())
    children_count = len(children)
    
    if children_count == 0:
        return
    
    # Beregn total vinkel for barna
    total_angle = end_angle - start_angle
    
    # Fordel vinkler jevnt mellom barna
    angle_step = total_angle / children_count
    
    for i, child_key in enumerate(children):
        # Beregn vinkel for dette barnet
        child_angle = end_angle - (i + 0.5) * angle_step
        
        # Beregn posisjon
        x, y = pol2cart(LEVEL_RADII[current_level], child_angle)
        
        # Lagre posisjon med full sti som nøkkel for å unngå kollisjoner
        full_key = f"{parent_key}|{child_key}"
        positions[full_key] = (x, y, child_angle)
        
        # Rekursivt beregn posisjoner for barnets barn
        if 'children' in children_dict[child_key] and len(children_dict[child_key]['children']) > 0:
            child_start = end_angle - (i + 1) * angle_step
            child_end = end_angle - i * angle_step
            
            calculate_child_positions(
                children_dict[child_key]['children'],
                positions,
                full_key,
                (x, y),
                child_angle,
                child_start,
                child_end,
                current_level + 1,
                max_levels,
                angle_per_node
            )

def count_nodes_by_level(hierarchy, max_levels=4):
    """
    Teller antall noder på hvert nivå i hierarkiet.
    
    Parameters:
    -----------
    hierarchy : dict
        Hierarkisk struktur av assosiasjoner.
    max_levels : int, optional
        Maksimalt antall nivåer å telle.
        
    Returns:
    --------
    list
        Liste med antall noder på hvert nivå.
    """
    counts = [0] * max_levels
    
    def count_recursive(node_dict, level=0):
        if level >= max_levels:
            return
        
        counts[level] += len(node_dict)
        
        for key, value in node_dict.items():
            if 'children' in value:
                count_recursive(value['children'], level + 1)
    
    count_recursive(hierarchy)
    return counts

def count_children(node, max_depth=3):
    """
    Teller antall barn for en node rekursivt.
    
    Parameters:
    -----------
    node : dict
        Node i hierarkiet.
    max_depth : int, optional
        Maksimal dybde å telle.
        
    Returns:
    --------
    int
        Antall barn.
    """
    if max_depth <= 0 or 'children' not in node or not node['children']:
        return 0
    
    count = len(node['children'])
    for child in node['children'].values():
        count += count_children(child, max_depth - 1)
    
    return count

def pol2cart(radius, angle):
    """
    Konverterer polare koordinater til kartesiske.
    
    Parameters:
    -----------
    radius : float
        Radius.
    angle : float
        Vinkel i radianer.
        
    Returns:
    --------
    tuple
        (x, y) koordinater.
    """
    return radius * np.cos(angle), radius * np.sin(angle)

# ===== VISUALISERING =====

def create_visualization(hierarchy, level_names, title_text=None, max_levels=4, save_path=None):
    """
    Lager visualiseringen basert på hierarkiet.
    
    Parameters:
    -----------
    hierarchy : dict
        Hierarkisk struktur av assosiasjoner.
    level_names : list
        Liste med navn på nivåene.
    title_text : str, optional
        Teksten som skal vises i sentrum av visualiseringen.
        Hvis None, vil brukeren bli spurt om å angi tekst.
    max_levels : int, optional
        Maksimalt antall nivåer å vise.
    save_path : str, optional
        Filsti for å lagre visualiseringen.
    """
    if hierarchy is None:
        print("Ingen data å visualisere.")
        return
    
    # Spør brukeren om tekst i midten hvis ikke spesifisert
    if title_text is None:
        title_text = input("Skriv inn tekst som skal vises i midten (trykk Enter for tom tekst): ") or ""
    
    # Beregn posisjoner for alle noder
    positions = calculate_positions(hierarchy, max_levels)
    
    # Oppretter figur med spesifisert bakgrunnsfarge og størrelse
    fig = plt.figure(figsize=FIGSIZE, facecolor=BACKGROUND_COLOR)
    ax = fig.add_subplot(111) 
    ax.set_facecolor(BACKGROUND_COLOR)
    ax.set_aspect('equal')
    ax.axis('off')  # Skjuler aksene
    
    # Tegner sentrum med sentrum-tekst
    ax.add_patch(plt.Circle((0, 0), CENTER_RADIUS, color=CENTER_CIRCLE_COLOR, alpha=CENTER_CIRCLE_ALPHA, zorder=10))
    ax.text(0, 0, title_text, ha='center', va='center', fontsize=CENTER_FONT_SIZE, fontweight='bold', color='black', zorder=11)
    
    # Tegner sirkler for å markere de forskjellige nivåene
    for i in range(min(max_levels, len(LEVEL_RADII))):
        ax.add_patch(plt.Circle((0, 0), LEVEL_RADII[i], fill=False, color=CIRCLE_OUTLINE_COLOR, linestyle='-', linewidth=0.5, zorder=2))
    
    # Tegn forbindelser og noder
    draw_connections(ax, hierarchy, positions, max_levels)
    
    # Legg til forklaringstekst for nivåer
    #add_level_legend(ax, level_names, max_levels)
    
    # Setter grenser for plottet med litt mer margin
    margin = 1.2
    if max_levels > 3:
        margin = 1.3  # Større margin for flere nivåer
    ax.set_xlim(-margin, margin)
    ax.set_ylim(-margin, margin)
    
    # Justerer layout
    plt.tight_layout()
    
    # Lagre figuren hvis en sti er angitt
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Visualisering lagret til: {save_path}")
    
    # Vis figuren og hold den åpen til brukeren lukker den
    plt.show()

def draw_connections(ax, hierarchy, positions, max_levels=4):
    """
    Tegner forbindelser mellom noder i hierarkiet.
    
    Parameters:
    -----------
    ax : matplotlib.axes.Axes
        Axes-objekt å tegne på.
    hierarchy : dict
        Hierarkisk struktur av assosiasjoner.
    positions : dict
        Dictionary med posisjoner for alle noder.
    max_levels : int, optional
        Maksimalt antall nivåer å vise.
    """
    # Tildel farger til primærassosiasjonene
    primary_keys = list(hierarchy.keys())
    primary_colors = {key: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, key in enumerate(primary_keys)}
    
    # Tegn forbindelser fra sentrum til primærassosiasjoner
    center_x, center_y = positions['center']
    
    for key in primary_keys:
        if key in positions:
            x, y, angle = positions[key]
            color = primary_colors[key]
            
            # Tegn linje fra sentrum til primærassosiasjon
            ax.plot([center_x, x], [center_y, y], color=color, alpha=LINE_ALPHA, linewidth=LEVEL_LINE_WIDTHS[0], zorder=1)
            
            # Tegn primærassosiasjonspunkt
            ax.add_patch(plt.Circle((x, y), LEVEL_CIRCLE_SIZES[0], color=color, alpha=0.9, zorder=5))
            
            # Plasser primærtekst med primærvinkelen som referanse for tekstretning
            place_text_radially(ax, key, LEVEL_RADII[0], angle, LEVEL_FONT_SIZES[0], LEVEL_TEXT_COLORS[0], LEVEL_MAX_TEXT_LENGTHS[0], bold=True, primary_angle=angle)
            
            # Tegn forbindelser til barn rekursivt, send med primærvinkelen
            draw_child_connections(ax, hierarchy[key]['children'], positions, key, (x, y), color, 1, max_levels, angle)

def draw_child_connections(ax, children_dict, positions, parent_key, parent_pos, color, current_level, max_levels, primary_angle):
    """
    Tegner forbindelser til barn rekursivt.
    
    Parameters:
    -----------
    ax : matplotlib.axes.Axes
        Axes-objekt å tegne på.
    children_dict : dict
        Dictionary med barn.
    positions : dict
        Dictionary med posisjoner for alle noder.
    parent_key : str
        Nøkkel for foreldrenoden.
    parent_pos : tuple
        Posisjon for foreldrenoden (x, y).
    color : str
        Farge for denne grenen av hierarkiet.
    current_level : int
        Gjeldende nivå (0-basert).
    max_levels : int
        Maksimalt antall nivåer.
    primary_angle : float
        Primærvinkelen for denne grenen, brukes for å sikre konsistent tekstretning.
    """
    # Stopp rekursjon hvis vi har nådd maksimalt nivå
    if current_level >= max_levels:
        return
    
    parent_x, parent_y = parent_pos
    
    for child_key in children_dict.keys():
        full_key = f"{parent_key}|{child_key}"
        
        if full_key in positions:
            x, y, angle = positions[full_key]
            
            # Tegn linje fra forelder til barn
            ax.plot([parent_x, x], [parent_y, y], color=color, alpha=LINE_ALPHA, linewidth=LEVEL_LINE_WIDTHS[current_level], zorder=1)
            
            # Tegn barnepunkt
            ax.add_patch(plt.Circle((x, y), LEVEL_CIRCLE_SIZES[current_level], color=color, alpha=0.7, zorder=4))
            
            # Plasser barnetekst med primærvinkelen som referanse for tekstretning
            place_text_radially(ax, child_key, LEVEL_RADII[current_level], angle, LEVEL_FONT_SIZES[current_level], LEVEL_TEXT_COLORS[current_level], LEVEL_MAX_TEXT_LENGTHS[current_level], primary_angle=primary_angle)
            
            # Rekursivt tegn forbindelser til barnets barn, send med samme primærvinkel
            if 'children' in children_dict[child_key] and len(children_dict[child_key]['children']) > 0:
                draw_child_connections(ax, children_dict[child_key]['children'], positions, full_key, (x, y), color, current_level + 1, max_levels, primary_angle)

def place_text_radially(ax, text, radius, angle, fontsize, color, max_length, bold=False, reference_angle=None, primary_angle=None):
    """
    Plasserer tekst radiellt med riktig justering og rotasjon.
    Bryter teksten med linjeskift hvis den er for lang.
    Bruker primærvinkelen for å sikre konsistent tekstretning innenfor grupper.
    """
    # Bryt teksten med linjeskift hvis den er for lang
    text_str = str(text)
    if len(text_str) > max_length:
        # Finn et passende sted å bryte teksten (ved mellomrom)
        break_point = text_str[:max_length].rfind(' ')
        if break_point == -1:  # Ingen mellomrom funnet, bryt ved maks lengde
            break_point = max_length
        
        # Legg inn linjeskift
        text_str = text_str[:break_point] + '\n' + text_str[break_point:].strip()
    
    # Beregn tekstposisjon
    text_radius = radius + TEXT_OFFSET
    text_x, text_y = pol2cart(text_radius, angle)
    
    # Bestem tekstretning basert på primærvinkelen
    if primary_angle is not None:
        # Konverter til grader for enklere sammenligning
        primary_degrees = np.degrees(primary_angle) % 360
        
        # Bestem om teksten skal vende mot høyre eller venstre basert på primærvinkelen
        if 90 < primary_degrees < 270:
            # Primærvinkel er i venstre halvdel, all tekst i gruppen skal vende mot venstre
            ha = 'right'
            rotation = np.degrees(angle) - 180
        else:
            # Primærvinkel er i høyre halvdel, all tekst i gruppen skal vende mot høyre
            ha = 'left'
            rotation = np.degrees(angle)
    else:
        # Ingen primærvinkel tilgjengelig, bruk standard logikk
        direction_angle = reference_angle if reference_angle is not None else angle
        direction_degrees = np.degrees(direction_angle) % 360
        
        if 90 < direction_degrees < 270:
            ha = 'right'
            rotation = np.degrees(angle) - 180
        else:
            ha = 'left'
            rotation = np.degrees(angle)
    
    # Plasser tekst med linjeskift
    ax.text(text_x, text_y, text_str, ha=ha, va='center', fontsize=fontsize,
            rotation=rotation, rotation_mode='anchor',
            fontweight='bold' if bold else 'normal', color=color, zorder=6)


def add_level_legend(ax, level_names, max_levels):
    """
    Legger til forklaringstekst for nivåer.
    
    Parameters:
    -----------
    ax : matplotlib.axes.Axes
        Axes-objekt å tegne på.
    level_names : list
        Liste med navn på nivåene.
    max_levels : int
        Maksimalt antall nivåer.
    """
    # Plasser forklaringstekst i nedre høyre hjørne
    legend_x = 0.95
    legend_y = -0.95
    
    # Legg til tittel
    ax.text(legend_x, legend_y, "Nivåer:", ha='right', va='bottom', fontsize=10, fontweight='bold')
    
    # Legg til nivånavn
    for i in range(min(max_levels, len(level_names))):
        y_pos = legend_y + 0.05 * (i + 1)
        ax.text(legend_x, y_pos, f"{i+1}: {level_names[i]}", ha='right', va='bottom', 
                fontsize=9, color=LEVEL_TEXT_COLORS[i])

# ===== HOVEDFUNKSJON =====

def create_association_dendrogram(excel_file=None, title_text=None, max_levels=4, save_path=None):
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
        
    max_levels : int, optional
        Maksimalt antall nivåer å vise.
        
    save_path : str, optional
        Filsti for å lagre visualiseringen.
    """
    # Last inn data
    hierarchy_data = load_association_data(excel_file)
    
    if hierarchy_data is not None:
        hierarchy, level_names = hierarchy_data
        print(hierarchy.keys())
        
        # Begrens antall nivåer til det som er tilgjengelig
        actual_max_levels = min(max_levels, len(level_names))
        
        # Lag visualisering
        create_visualization(hierarchy, level_names, title_text, actual_max_levels, save_path)
    else:
        print("Kunne ikke lage visualisering på grunn av problemer med datainnlesing.")

# ===== KOMMANDOLINJE-GRENSESNITT =====

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lag en visualisering av assosiasjoner fra en Excel-fil.')
    parser.add_argument('--data', help='Filsti til Excel-filen med assosiasjonsdata')
    parser.add_argument('--title', help='Tekst som skal vises i sentrum (standard: tom tekst)')
    parser.add_argument('--levels', type=int, default=4, help='Maksimalt antall nivåer å vise (standard: 4)')
    parser.add_argument('--save', help='Filsti for å lagre visualiseringen')
    
    args = parser.parse_args()
    
    create_association_dendrogram(args.data, args.title, args.levels, args.save)
