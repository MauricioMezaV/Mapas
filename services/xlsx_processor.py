import pandas as pd
import simplekml
import os
from shapely import wkt

def export_zonas_to_kml(zonas_xlsx, output_dir):
    """
    Convierte un archivo zonas.xlsx (con columnas: Nombre, Poligono en WKT) a uno o varios archivos KML de polígonos.
    Retorna una lista con los nombres de los archivos generados.
    """
    df = pd.read_excel(zonas_xlsx)
    archivos = []
    # Un solo archivo para todas las zonas
    kml = simplekml.Kml()
    for _, row in df.iterrows():
        nombre = str(row['Nombre'])
        poligono = wkt.loads(row['Poligono'])
        coords = [(x, y) for x, y in poligono.exterior.coords]
        pol = kml.newpolygon(name=nombre, outerboundaryis=coords)
        pol.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.green)
    nombre_archivo = "zonas.kml"
    kml.save(os.path.join(output_dir, nombre_archivo))
    archivos.append(nombre_archivo)
    return archivos

def export_clientes_to_kml(clientes_xlsx, output_dir, max_por_kml=2000):
    """
    Convierte un archivo clientes.xlsx (con columnas: Nombre, Latitud, Longitud, Tipo de Cliente)
    en uno o varios archivos KML de puntos, separados por tipo de cliente y tamaño máximo.
    Retorna una lista con los nombres de los archivos generados.
    """
    df = pd.read_excel(clientes_xlsx)
    tipos = df['Tipo de Cliente'].unique()
    archivos = []
    for tipo in tipos:
        df_tipo = df[df['Tipo de Cliente'] == tipo]
        total = len(df_tipo)
        partes = (total // max_por_kml) + (1 if total % max_por_kml else 0)
        for i in range(partes):
            kml = simplekml.Kml()
            chunk = df_tipo.iloc[i*max_por_kml:(i+1)*max_por_kml]
            for _, row in chunk.iterrows():
                nombre = str(row['Nombre'])
                lat = float(row['Latitud'])
                lon = float(row['Longitud'])
                kml.newpoint(name=nombre, coords=[(lon, lat)])
            nombre_archivo = f"{tipo}_clientes_{i+1}.kml" if partes > 1 else f"{tipo}_clientes.kml"
            kml.save(os.path.join(output_dir, nombre_archivo))
            archivos.append(nombre_archivo)
    return archivos