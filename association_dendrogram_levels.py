import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
#import matplotlib.patches as patches
#import math
import argparse
#import os
import tkinter as tk
from tkinter import filedialog
import matplotlib
import textwrap

# Sett backend til interaktiv visning
matplotlib.use('TkAgg')

# ===== KONSTANTER FOR TILPASNING =====

# Figurstørrelse
FIGSIZE = (14, 10)  # Størrelse på figuren i tommer (bredde, høyde)

# Maksimalt antall nivåer å vise
MAX_LEVELS = 4  

# Startvinkel for første assosiasjon (i grader)
START_ANGLE_DEGREES = 85  

# Mellomrom mellom grupper som en andel av en assosiasjonsplass
SPACING_FACTOR = 0.5  # Mellomrom tilsvarende 50% av plassen til én assosiasjon

# Fontstørrelser
CENTER_FONT_SIZE = 18            # Fontstørrelse for sentrum-tekst
LEVEL_FONT_SIZES = [9, 9, 9, 9]  # Fontstørrelser for nivå 1-4

# Maksimal tekstlengde per nivå før teksten brytes i to linjer
LEVEL_MAX_TEXT_LENGTHS = [15, 20, 20, 20]  # Nivå 1-4

# Tekstplassering
TEXT_OFFSET = 0.03               # Avstand fra markør til tekst

# Radier for de forskjellige nivåene
CENTER_RADIUS = 0.1             # Radius for sentrum-sirkel
LEVEL_RADII = [0.20, 0.5, 0.85, 1.05]  # Radier for nivå 1-4

# Farger og størrelser for sirkler
CENTER_CIRCLE_COLOR = '#87CEFA'  # Lyseblå bakgrunn for sentrum
CENTER_CIRCLE_ALPHA = 0.7        # Gjennomsiktighet for sentrum-sirkel
LEVEL_MARKER_SIZES = [0.008]*4  # Markørstørrelse for nivå 1-4
LEVEL_OUTLINE_COLOR = '#FFFFFF' # Hvit farge på de store sirklene som markerer nivåer

# Linjestiler
LEVEL_LINE_WIDTH = [1]*4 #[1, 0.8, 0.7, 0.6]  # Linjetykkelser for nivå 1-4
LINE_ALPHA = 0.3                 # Gjennomsiktighet for linjer (0 = usynlig linje)
#LINE_TYPE = 'straight'  # ('curved' eller 'straight')
LINE_TYPE = 'curved'  # ('curved' eller 'straight')
CURVE_SHAPE = [0.3, 0.4]

# Tekstfarger
LEVEL_TEXT_COLORS = ['#333333', '#444444', '#555555', '#666666']  # Farger for nivå 1-4

# Bakgrunnsfarge
BACKGROUND_COLOR = '#FFFFFF'  

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
        print(list(hierarchy.keys()))
        print(f"Kolonner (nivåer): {list(df.columns)}")
        print(df.set_index([1,2]))
        
        return hierarchy, df

    except Exception as e:
        print(f"Feil ved lesing av data: {str(e)}")
        return None, None


def build_association_hierarchy(df):
    """
    Bygger en hierarkisk struktur av assosiasjoner fra datarammen.
    Håndterer manglende mellomliggende nivåer ved å legge dem inn som NaN i hierarkiet,
    men bare når det faktisk finnes assosiasjoner på dypere nivåer.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Dataramme med assosiasjonsdata.
    max_levels : int, optional
        Maksimalt antall nivåer å inkludere i hierarkiet.
        
    Returns:
    --------
    dict
        En dictionary med hierarkisk struktur av assosiasjoner.
    """
    hierarchy = {}
    
    # Begrens til maksimalt antall nivåer
    actual_columns = df.columns[:min(len(df.columns), MAX_LEVELS)]
    
    # Gå gjennom hver rad i datarammen
    for _, row in df.iterrows():
        # Sjekk at vi har en gyldig primærassosiasjon (første kolonne)
        if pd.isna(row[actual_columns[0]]) or row[actual_columns[0]] == '':
            continue  # Hopp over rader uten primærassosiasjon
        
        # Samle alle gyldige verdier fra raden
        values = []
        for col in actual_columns:
            if pd.notna(row[col]) and row[col] != '':
                values.append(row[col])
            else:
                values.append(None)
        
        # Legg til primærassosiasjon hvis den ikke finnes
        primary = values[0]
        if primary not in hierarchy:
            hierarchy[primary] = {'children': {}}
        
        current_dict = hierarchy[primary]['children']
        
        # Gå gjennom resten av nivåene
        for level in range(1, len(values)):
            value = values[level]
            
            # Hvis vi har en verdi på dette nivået
            if value is not None:
                if value not in current_dict:
                    current_dict[value] = {'children': {}}
                current_dict = current_dict[value]['children']
            else:
                # Sjekk om det finnes verdier på dypere nivåer
                if any(v is not None for v in values[level+1:]):
                    # Legg til en NaN-node
                    if "NaN" not in current_dict:
                        current_dict["NaN"] = {'children': {}}
                    current_dict = current_dict["NaN"]['children']
                else:
                    # Ingen verdier på dypere nivåer, så vi trenger ikke legge til NaN-noder
                    break
    
    return hierarchy

# ===== VINKLER OG POSISJONER =====



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
    angle : float
        
    Returns:
    --------
    tuple
        (x, y) koordinater.
    """
    return radius * np.cos(angle), radius * np.sin(angle)


def calculate_positions_radial(hierarchy):
    """
    Beregner posisjoner for alle assosiasjoner i hierarkiet.
    
    Parameters:
    -----------
    hierarchy : dict
        Hierarkisk struktur av assosiasjoner.
        
    Returns:
    --------
    dict
        Dictionary med posisjoner for alle assosiasjoner.
    """
    positions = {'center': (0, 0)}
    
    # Beregn total vinkel for hele sirkelen
    total_angle = 2 * np.pi
    
    # Startvinkel (konverter fra grader til radianer)
    start_angle = np.radians(START_ANGLE_DEGREES)
    
    # Beregn posisjoner for primærassosiasjoner (nivå 1)
    level1_keys = list(hierarchy.keys())
    level1_count = len(level1_keys)
    
    # Beregn effektivt antall noder for vinkelfordeling
    effective_count = sum(count_children(hierarchy[key], MAX_LEVELS-1) + 1 for key in level1_keys)
    angle_per_node = total_angle / (effective_count + level1_count * SPACING_FACTOR)
    
    current_angle = start_angle
    
    # Fordel primærassosiasjoner rundt sirkelen
    for i, key in enumerate(level1_keys):
        # Beregn antall barn for denne primærassosiasjonen
        children_count = count_children(hierarchy[key], MAX_LEVELS-1)
        effective_space = (children_count + 1) * angle_per_node
        
        # Plasser primærassosiasjonen i midten av sin tildelte plass
        node_angle = current_angle - effective_space / 2
        x, y = pol2cart(LEVEL_RADII[0], node_angle)
        positions[key] = (x, y, node_angle)
        
        # Beregn posisjoner for barn rekursivt
        if 'children' in hierarchy[key] and len(hierarchy[key]['children']) > 0:
            calculate_child_positions_radial(
                children_dict=hierarchy[key]['children'], 
                positions=positions, 
                parent_key=key, 
                start_angle=current_angle - effective_space,
                end_angle=current_angle,
                current_level=1,
                angle_per_node=angle_per_node
        )
        
        # Oppdater vinkel for neste primærassosiasjon
        current_angle -= effective_space
        
        # Legg til mellomrom mellom grupper
        if i < level1_count - 1:
            current_angle -= angle_per_node * SPACING_FACTOR
    
    return positions


def calculate_child_positions_radial(children_dict, positions, parent_key,
                             start_angle, end_angle, current_level, angle_per_node):
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
    start_angle : float
        Startvinkel for barnas område.
    end_angle : float
        Sluttvinkel for barnas område.
    current_level : int
        Gjeldende nivå (0-basert).
    angle_per_node : float
        Vinkel per node.
    """
    # Stopp rekursjon hvis vi har nådd maksimalt nivå
    if current_level >= MAX_LEVELS:
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
            
            calculate_child_positions_radial(
                children_dict=children_dict[child_key]['children'],
                positions=positions,
                parent_key=full_key,
                start_angle=child_start,
                end_angle=child_end,
                current_level=current_level + 1,
                angle_per_node=angle_per_node
            )

def calculate_positions_linear(hierarchy, orientation='horizontal', spacing=1.0, level_spacing=2.0):
    """
    Enklere versjon som beregner posisjoner for lineært dendrogram.
    
    Parameters:
    -----------
    hierarchy : dict
        Hierarkisk struktur av assosiasjoner
    orientation : str
        'horizontal' eller 'vertical'
    spacing : float
        Avstand mellom elementer på samme nivå
    level_spacing : float
        Avstand mellom nivåer
        
    Returns:
    --------
    dict
        Dictionary med posisjoner {'node_key': (x, y)}
    """
    positions = {}
    
    # Samle alle noder per nivå
    levels = {}  # {level: [node_keys]}
    
    def collect_nodes(node_dict, parent_key="", current_level=0):
        """Samler alle noder organisert per nivå"""
        if current_level >= MAX_LEVELS:
            return
            
        if current_level not in levels:
            levels[current_level] = []
            
        # Legg til noder på dette nivået
        for child_key, child_node in node_dict.items():
            if child_key == "NaN":
                continue
                
            full_key = f"{parent_key}|{child_key}" if parent_key else child_key
            levels[current_level].append(full_key)
            
            # Rekursivt for barn
            if 'children' in child_node:
                collect_nodes(child_node['children'], full_key, current_level + 1)
    
    # Samle alle noder
    collect_nodes(hierarchy)
    
    # Beregn posisjoner for alle nivåer
    for level, nodes in levels.items():
        for i, node_key in enumerate(nodes):
            if orientation.lower() == 'horizontal':
                # Horisontal: nivåer går fra venstre til høyre, elementer fordeles vertikalt
                x = level * level_spacing
                y = (i - len(nodes)/2 + 0.5) * spacing
            else:  # vertical
                # Vertikal: nivåer går fra topp til bunn, elementer fordeles horisontalt
                x = (i - len(nodes)/2 + 0.5) * spacing
                y = -level * level_spacing
            
            positions[node_key] = (x, y, 0)
    
    # Rot-posisjon
    if orientation.lower() == 'horizontal':
        positions['center'] = (-level_spacing, 0)
    else:
        positions['center'] = (0, level_spacing)
    
    print(f"Beregnet posisjoner for {len(positions)} noder")
    print(f"Nivåer: {list(levels.keys())}")
    print(f"Noder per nivå: {[len(nodes) for nodes in levels.values()]}")
    
    return positions


# ===== VISUALISERING =====

def draw_connections(ax, hierarchy, positions):
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
            
            # Tegn linje fra sentrum til primærassosiasjon basert på LINE_TYPE
            if LINE_TYPE.lower() == 'curved':
                draw_curved_line(ax, center_x, center_y, x, y, color, LEVEL_LINE_WIDTH[0])
            else:
                ax.plot([center_x, x], [center_y, y], color=color, alpha=LINE_ALPHA, 
                        linewidth=LEVEL_LINE_WIDTH[0], zorder=1)
            
            # Tegn primærassosiasjonspunkt
            ax.add_patch(plt.Circle((x, y), LEVEL_MARKER_SIZES[0], color=color, alpha=0.9, zorder=5))
            
            # Plasser primærtekst med primærvinkelen som referanse for tekstretning
            place_text_radially(
                ax=ax,
                text=key,
                angle=angle,
                radius=LEVEL_RADII[0],
                fontsize=LEVEL_FONT_SIZES[0],
                color=LEVEL_TEXT_COLORS[0],
                max_length=LEVEL_MAX_TEXT_LENGTHS[0],
                bold=True,
                primary_angle=angle
                )

            # Tegn forbindelser til barn rekursivt, send med primærvinkelen
            draw_child_connections(
                ax=ax,
                children_dict=hierarchy[key]['children'],
                positions=positions,
                parent_key=key,
                parent_pos=(x, y),
                color=color,
                current_level=1,
                primary_angle=angle
            )


def draw_child_connections(ax, children_dict, positions, parent_key, parent_pos, color, current_level, primary_angle):
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
    primary_angle : float
        Primærvinkelen for denne grenen, brukes for å sikre konsistent tekstretning.
    """
    # Stopp rekursjon hvis vi har nådd maksimalt nivå
    if current_level >= MAX_LEVELS:
        return
    
    parent_x, parent_y = parent_pos
    
    for child_key in children_dict.keys():
        full_key = f"{parent_key}|{child_key}"
        
        if full_key in positions:
            x, y, angle = positions[full_key]
            
            # Tegn linje fra forelder til barn basert på LINE_TYPE
            if LINE_TYPE.lower() == 'curved':
                draw_curved_line(ax, parent_x, parent_y, x, y, color, LEVEL_LINE_WIDTH[current_level])
            else:
                ax.plot([parent_x, x], [parent_y, y], color=color, alpha=LINE_ALPHA, 
                        linewidth=LEVEL_LINE_WIDTH[current_level], zorder=1)

            # Sjekk om dette er en NaN-node
            is_nan_node = child_key == "NaN"
           
            # Tegn barnepunkt bare hvis det ikke er en NaN-node
            if not is_nan_node:
                ax.add_patch(plt.Circle((x, y), LEVEL_MARKER_SIZES[current_level], color=color, alpha=0.7, zorder=4))
           
            # Plasser barnetekst bare hvis det ikke er en NaN-node
            if not is_nan_node:
                place_text_radially(
                    ax=ax,
                    text=child_key,
                    radius=LEVEL_RADII[current_level],
                    angle=angle,
                    fontsize=LEVEL_FONT_SIZES[current_level],
                    color=LEVEL_TEXT_COLORS[current_level],
                    max_length=LEVEL_MAX_TEXT_LENGTHS[current_level],
                    primary_angle=primary_angle
                )

            # Rekursivt tegn forbindelser til barnets barn, send med samme primærvinkel
            if 'children' in children_dict[child_key] and len(children_dict[child_key]['children']) > 0:
                #draw_child_connections(ax, children_dict[child_key]['children'], positions, full_key, (x, y), color, current_level + 1, primary_angle)
                draw_child_connections(
                    ax=ax,
                    children_dict=children_dict[child_key]['children'],
                    positions=positions,
                    parent_key=full_key,
                    parent_pos=(x, y),
                    color=color,
                    current_level=current_level + 1,
                    primary_angle=primary_angle
                )


def draw_curved_line(ax, x1, y1, x2, y2, color, linewidth):
    """
    Tegner en buet linje mellom to punkter som starter og slutter radielt,
    men buer seg mellom punktene.
    
    Parameters:
    -----------
    ax : matplotlib.axes.Axes
        Axes-objekt å tegne på.
    x1, y1 : float
        Koordinater for startpunktet.
    x2, y2 : float
        Koordinater for sluttpunktet.
    color : str
        Farge for linjen.
    linewidth : float
        Tykkelse for linjen.
    """
    # Sjekk om ett av punktene er sentrum (0,0)
    is_from_center = (abs(x1) < 1e-10 and abs(y1) < 1e-10) or (abs(x2) < 1e-10 and abs(y2) < 1e-10)
    
    # For linjer fra sentrum, bruk rette linjer
    if is_from_center:
        ax.plot([x1, x2], [y1, y2], color=color, alpha=LINE_ALPHA, linewidth=linewidth, zorder=1)
        return
    
    # Beregn radielle vektorer for hvert punkt
    # Disse vektorene peker fra sentrum til punktet
    v1_x, v1_y = x1, y1
    v2_x, v2_y = x2, y2
    
    # Normaliser vektorene
    len1 = np.sqrt(v1_x**2 + v1_y**2)
    len2 = np.sqrt(v2_x**2 + v2_y**2)
    
    if len1 > 0:
        v1_x /= len1
        v1_y /= len1
    
    if len2 > 0:
        v2_x /= len2
        v2_y /= len2
    
    # Beregn avstand mellom punktene
    dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    # Beregn kontrollpunkter langs de radielle vektorene
    # Dette sikrer at kurven starter og slutter radielt
    ctrl1_x = x1 + v1_x * dist * CURVE_SHAPE[0]
    ctrl1_y = y1 + v1_y * dist * CURVE_SHAPE[0]
    
    ctrl2_x = x2 - v2_x * dist * CURVE_SHAPE[1]
    ctrl2_y = y2 - v2_y * dist * CURVE_SHAPE[1]
    
    # Lag en Path med en kubisk Bézier-kurve
    path = matplotlib.path.Path([
        (x1, y1),          # Startpunkt
        (ctrl1_x, ctrl1_y), # Første kontrollpunkt
        (ctrl2_x, ctrl2_y), # Andre kontrollpunkt
        (x2, y2)           # Sluttpunkt
    ], [
        matplotlib.path.Path.MOVETO,
        matplotlib.path.Path.CURVE4,
        matplotlib.path.Path.CURVE4,
        matplotlib.path.Path.CURVE4
    ])
    
    # Tegn kurven
    patch = matplotlib.patches.PathPatch(
        path, 
        facecolor='none', 
        edgecolor=color, 
        linewidth=linewidth, 
        alpha=LINE_ALPHA,
        zorder=1
    )
    ax.add_patch(patch)


def place_text_radially(ax, text, radius, angle, fontsize, color, max_length, bold=False, primary_angle=None):
    """
    Plasserer tekst radiellt med riktig justering og rotasjon.
    Bryter teksten med linjeskift hvis den er for lang.
    Bruker primærvinkelen for å sikre konsistent tekstretning innenfor grupper.
    
    Parameters:
    -----------
    ax : matplotlib.axes.Axes
        Axes-objekt å tegne på.
    text : str
        Teksten som skal plasseres.
    radius : float
        Radius for plassering av teksten.
    angle : float
        Vinkel (i radianer) for plassering av teksten.
    fontsize : int
        Fontstørrelse for teksten.
    color : str
        Farge for teksten.
    max_length : int
        Maksimal tekstlengde før linjeskift.
    bold : bool, optional
        Om teksten skal være uthevet. Standard er False.
    primary_angle : float, optional
        Primærvinkel for å sikre konsistent tekstretning innenfor grupper.
        Hvis None, brukes angle.
    """
    # Bryt teksten med linjeskift hvis den er for lang
    text_str = textwrap.fill(str(text), width=max_length, break_long_words=True, break_on_hyphens=True)

    # Beregn tekstposisjon
    text_radius = radius + TEXT_OFFSET
    text_x, text_y = pol2cart(text_radius, angle)
    
    # Bestem hvilken vinkel som skal brukes for å avgjøre tekstretning
    direction_angle = primary_angle if primary_angle is not None else angle
    
    # Konverter til grader for sammenligning
    direction_degrees = np.degrees(direction_angle) % 360
    
    # Bestem tekstretning basert på vinkelen
    # Hvis vinkelen er i venstre halvdel (90-270 grader), vend teksten mot venstre
    # Ellers vend teksten mot høyre
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


def create_visualization(hierarchy, orient=None, title_text=None, max_levels=None, save_path=None):
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
        Maksimalt antall nivåer å vise. Hvis None, brukes den globale MAX_LEVELS.
    save_path : str, optional
        Filsti for å lagre visualiseringen.
    """
    if hierarchy is None:
        print("Ingen data å visualisere.")
        return
    
    # Bruk global konstant hvis ikke spesifisert
    actual_max_levels = max_levels if max_levels is not None else MAX_LEVELS
    
    # Spør brukeren om tekst i midten hvis ikke spesifisert
    if title_text is None:
        title_text = input("Skriv inn tekst som skal vises i midten (trykk Enter for tom tekst): ") or ""
        
    if not orient:
            orientation = 'radial'
    else:
        orient_lower = str(orient).lower().strip()
        if orient_lower in ['h', 'horizontal']:
            orientation = 'horizontal'
        elif orient_lower in ['v', 'vertical']:
            orientation = 'vertical'
        else:  # Alt annet (r, radial, ugyldig) -> radial
            orientation = 'radial'

    # Beregn posisjoner for alle noder
    if orientation=='radial':
        positions = calculate_positions_radial(hierarchy)
    
    else:
        positions = calculate_positions_linear(hierarchy, orientation)
    
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
    for i in range(min(actual_max_levels, len(LEVEL_RADII))):
        ax.add_patch(plt.Circle((0, 0), LEVEL_RADII[i], fill=False, color=LEVEL_OUTLINE_COLOR, linestyle='-', linewidth=0.5, zorder=2))
    
    # Tegn forbindelser og noder
    draw_connections(ax, hierarchy, positions)
      
    # Setter grenser for plottet med litt mer margin
    margin = 1.2
    if actual_max_levels > 3:
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



# ===== HOVEDFUNKSJON =====

def create_association_dendrogram(excel_file=None, title_text=None, save_path=None, orient=None):
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
        hierarchy, df = hierarchy_data
        
        # Begrens antall nivåer til det som er tilgjengelig
        actual_max_levels = min(MAX_LEVELS, len(df.columns))
        
        # Lag visualisering
        create_visualization(hierarchy, orient, title_text, actual_max_levels, save_path)

        return hierarchy, df
    else:
        print("Kunne ikke lage visualisering på grunn av problemer med datainnlesing.")


# ===== KOMMANDOLINJE-GRENSESNITT =====

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lag en visualisering av assosiasjoner fra en Excel-fil.')
    parser.add_argument('--data', help='Filsti til Excel-filen med assosiasjonsdata')
    parser.add_argument('--title', help='Tekst som skal vises i sentrum (standard: tom tekst)')
    parser.add_argument('--save', help='Filsti for å lagre visualiseringen')
    parser.add_argument('--orient', help='[r]adial, [h]orizontal eller [v]ertical')
    
    args = parser.parse_args()
    
    h, df = create_association_dendrogram(args.data, args.title, args.save, args.orient)
