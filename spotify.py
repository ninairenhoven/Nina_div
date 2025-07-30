import os
import pandas as pd
from pathlib import Path

dir = Path.home().joinpath("Opinion AS/Opinion SharePoint - Spotify/Spillelister")
files = os.listdir(dir)
csv_files = [f for f in files if f.endswith(".csv")]

resp_file = dir.joinpath('Spotify vervede.xlsx')

track_df = pd.DataFrame()

for file in csv_files:
    print(file, end=" ")
    data = pd.read_csv(dir.joinpath(file))
    tracks = data.set_index("#")["Spotify Track Id"]
    resp_id = Path(file).stem
    track_df[resp_id] = tracks

track_df = track_df.T
track_df.index = track_df.index.astype(int)

df = pd.read_excel(resp_file)
df = df.set_index('Response ID')
df = df.drop(columns=df.columns[0])
df.columns = df.columns.str.split(":").str[0]

df = df.merge(track_df, left_index=True, right_index=True)

output_file = dir.joinpath('data_med_tracks.xlsx')
df.to_excel(output_file)