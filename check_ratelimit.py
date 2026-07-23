import sqlite3
conn = sqlite3.connect('archivo_hytale.db')
c1 = conn.execute("SELECT COUNT(*) FROM mods WHERE platform='curseforge' AND description IS NULL").fetchone()[0]
c2 = conn.execute("SELECT COUNT(*) FROM mods WHERE platform='curseforge'").fetchone()[0]
print(f'CF mods total:           {c2}')
print(f'CF mods missing desc:    {c1}')
print(f'Extra API calls needed:  {c1} calls x 2s delay = {c1*2//60} min backfill')
print(f'Future runs (1000 mods): 1000 extra calls x 2s = {1000*2//60} min per weekly run')
conn.close()
