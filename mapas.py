import geopandas as gpd
import pandas as pd
import re
import os
from fiona import listlayers

# Función para extraer pares clave:valor de la columna Description y convertirlos en columnas separadas
def split_description_to_columns(df):
    def parse_desc(desc):
        if pd.isnull(desc):
            return {}
        # Busca patrones tipo "clave: valor"
        pairs = re.findall(r'([^:<>\n]+):\s*([^<>\n]+)', desc)
        return {k.strip(): v.strip() for k, v in pairs}

    desc_dicts = df['Description'].apply(parse_desc)
    desc_df = pd.DataFrame(desc_dicts.tolist())
    # Unir zona, descripción separada y geometría (como WKT)
    df['geometry_wkt'] = df.geometry.apply(lambda g: g.wkt)
    resultado = pd.concat([df[['Name']], desc_df, df[['geometry_wkt']]], axis=1)
    return resultado

# Reemplaza o agrega un valor en la descripción según un patrón
def replace_or_append(pattern, value, desc):
    if re.search(pattern, desc):
        return re.sub(pattern, value, desc)
    elif value:
        # Si no existe, agregar al final con salto de línea si es necesario
        return (desc + ('\n' if desc and not desc.endswith('\n') else '') + value).strip()
    return desc

# Extrae el tipo de cliente desde la descripción
def get_tipo_cliente(desc):
    if pd.isnull(desc):
        return None
    match = re.search(r'Tipo de cliente:\s*([^\n<]+)', desc)
    return match.group(1).strip() if match else None

# Actualiza la descripción de un punto con información del polígono correspondiente
def update_description(row):
    desc_point = row['Description_point'] or ''
    desc_poly = row['Description_polygon']
    desc_poly_str = str(desc_poly) if pd.notnull(desc_poly) else ''
    # Extrae los campos relevantes del polígono
    cod_transporte = re.search(r'Cod\. Transporte:\s*([^\n<]+)', desc_poly_str)
    transporte = re.search(r'Transporte:\s*([^\n<]+)', desc_poly_str)
    frecuencia = re.search(r'Frecuencia:\s*([^\n<]+)', desc_poly_str)
    desc = desc_point

    # Reemplaza o agrega los campos en la descripción del punto
    if cod_transporte:
        desc = replace_or_append(r'Cod\. Transporte:\s*[^\n<]+', f'Cod. Transporte: {cod_transporte.group(1).strip()}', desc)
    if transporte:
        desc = replace_or_append(r'Transporte:\s*[^\n<]+', f'Transporte: {transporte.group(1).strip()}', desc)
    if frecuencia:
        desc = replace_or_append(r'Frecuencia:\s*[^\n<]+', f'Frecuencia: {frecuencia.group(1).strip()}', desc)
    return desc.strip()

# Importa todas las capas del archivo KML y las une en un solo GeoDataFrame

kml_file = 'ZRyLocales_Rancagua.kml'
layers = listlayers(kml_file)
gdfs = [gpd.read_file(kml_file, driver='KML', layer=layer) for layer in layers]
mapf_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:4326")

# Separa los datos por tipo de geometría (polígonos y puntos)
map_polygons = mapf_gdf[mapf_gdf.geometry.type == 'Polygon']
map_points = mapf_gdf[mapf_gdf.geometry.type == 'Point']

# Extrae el tipo de cliente de la descripción de cada punto
map_points['tipo_cliente'] = map_points['Description'].apply(get_tipo_cliente)

# Diccionario para identificar los diferentes tipos de clientes
tipos_clientes = {
    'supermercados': 'Supermercados',
    'foodservice': 'Foodservice',
    'tradicional': 'Tradicional',
    'industriales': 'Industriales'
}

columns_to_save = ['Name', 'Description', 'geometry']
max_elements = 2000  # Máximo de elementos por capa

csv_chunks = []  # Lista para almacenar los DataFrames de cada chunk

# Procesa cada tipo de cliente por separado
for tipo_key, tipo_val in tipos_clientes.items():
    # Filtra los puntos del tipo de cliente actual
    mapa_tipo = map_points[map_points['tipo_cliente'] == tipo_val].reset_index(drop=True)
    if mapa_tipo.empty:
        continue
    # Realiza un join espacial para asociar cada punto con el polígono correspondiente
    joined = gpd.sjoin(
        mapa_tipo,
        map_polygons[['Name', 'Description', 'geometry']],
        how='left',
        predicate='within',
        lsuffix='point',
        rsuffix='polygon'
    )
    # Actualiza la descripción del punto con información del polígono
    joined['Description'] = joined.apply(update_description, axis=1)
    # Usa el nombre del polígono como nombre del punto
    joined['Name'] = joined['Name_polygon']
    total = len(joined)
    # Divide en chunks para guardar archivos más pequeños
    for i in range(0, total, max_elements):
        chunk = joined.iloc[i:i+max_elements]
        # Guarda el chunk como archivo KML
        chunk[columns_to_save].to_file(
            f'puntos_{tipo_key}_con_nombre_de_poligono_{i//max_elements + 1}.kml',
            driver='KML'
        )
        # Prepara el chunk para guardar como CSV
        chunk_csv = chunk[columns_to_save].copy()
        # Procesa la columna Description para extraer los campos requeridos
        def parse_desc(desc):
            if pd.isnull(desc):
                return {}
            pairs = re.findall(r'([^:<>\n]+):\s*([^<>\n]+)', desc)
            return {k.strip(): v.strip() for k, v in pairs}
        desc_df = chunk_csv['Description'].apply(parse_desc).apply(pd.Series)
        # Selecciona solo las columnas requeridas para el CSV
        columnas_requeridas = [
            'Código', 'Local', 'Calle', 'Población', 'Tipo de cliente',
            'Cod. Transporte', 'Transporte', 'Frecuencia',
            'Kilos Promedio Semanal', 'Latitud', 'Longitud'
        ]
        for col in columnas_requeridas:
            if col not in desc_df.columns:
                desc_df[col] = None
        # Une el nombre con los campos extraídos
        final_csv = pd.concat([chunk_csv[['Name']], desc_df[columnas_requeridas]], axis=1)
        csv_chunks.append(final_csv)

# Une todos los chunks y guarda un solo archivo CSV con todos los puntos procesados
if csv_chunks:
    all_points_df = pd.concat(csv_chunks, ignore_index=True)
    all_points_df.to_csv('ClientesActualizados.csv', index=False)