import os
import pandas as pd
import geopandas as gpd
import fiona
import re

def listlayers(kml_file):
    return fiona.listlayers(kml_file)

def get_column_case_insensitive(df, candidates):
    for col in df.columns:
        for cand in candidates:
            if col.lower() == cand.lower():
                return col
    return None

def parse_desc(desc):
    if pd.isnull(desc):
        return {}
    if '<br>' in desc:
        parts = desc.split('<br>')
    else:
        parts = desc.split(',')
    result = {}
    for part in parts:
        match = re.match(r'([^:<>\n]+):\s*([^<>\n]+)', part)
        if match:
            k, v = match.groups()
            result[k.strip()] = v.strip()
    return result

def process_kml(kml_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    layers = listlayers(kml_file)

    gdfs = [gpd.read_file(kml_file, driver='KML', layer=layer) for layer in layers]
    mapf_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:4326")
    print("Columnas encontradas en el KML:", list(mapf_gdf.columns))

    name_col = get_column_case_insensitive(mapf_gdf, ['Name', 'name', 'NOMBRE', 'nombre', 'title'])
    desc_col = get_column_case_insensitive(mapf_gdf, ['Description', 'description', 'DESCRIPCION', 'descripcion', 'detalle'])
    geom_col = get_column_case_insensitive(mapf_gdf, ['geometry', 'geom', 'Geometry'])

    if name_col is None:
        raise ValueError("No se encontró una columna de nombre ('Name', 'name', 'NOMBRE') en el archivo KML.")
    if desc_col is None:
        raise ValueError("No se encontró una columna de descripción ('Description', 'description', 'DESCRIPCION') en el archivo KML.")
    if geom_col is None:
        raise ValueError("No se encontró una columna de geometría ('geometry', 'geom', 'Geometry') en el archivo KML.")
    
    map_polygons = mapf_gdf[mapf_gdf.geometry.type == 'Polygon'][[name_col, desc_col, geom_col]]
    map_points = mapf_gdf[mapf_gdf.geometry.type == 'Point'][[name_col, desc_col, geom_col]]

    print("Cantidad de clientes:", len(map_points))
    print("Cantidad de zonas de reparto:", len(map_polygons))

    if map_points.empty:
        raise ValueError("No se encontraron clientes en el archivo KML.")
    if map_polygons.empty:
        raise ValueError("No se encontraron zonas en el archivo KML.")

    # Crear archivo Excel de polígonos antes del sjoin
    polygons_for_export = map_polygons.copy()
    polygons_for_export = polygons_for_export.rename(columns={
        name_col: "zona_nombre",
        desc_col: "zona_descripcion",
        geom_col: "zona_geometry"
    })
    
    # Convertir geometría a WKT para el Excel
    polygons_for_export['zona_geometry'] = polygons_for_export['zona_geometry'].apply(lambda g: g.wkt if pd.notnull(g) else None)
    
    # Expandir las descripciones de los polígonos
    zona_desc_expanded = polygons_for_export['zona_descripcion'].apply(parse_desc).apply(pd.Series)
    if not zona_desc_expanded.empty:
        zona_desc_expanded = zona_desc_expanded.add_prefix('zona_')
    
    # Crear DataFrame final para polígonos
    polygons_result = pd.concat([
        polygons_for_export[['zona_nombre', 'zona_geometry']].reset_index(drop=True),
        zona_desc_expanded.reset_index(drop=True)
    ], axis=1)
    
    # Ordenar columnas: nombre, descripción expandida, geometría
    cols_zona_base = ['zona_nombre']
    cols_zona_desc = [c for c in polygons_result.columns if c.startswith('zona_') and c not in ['zona_nombre', 'zona_geometry']]
    cols_zona_geom = ['zona_geometry']
    polygons_final_cols = cols_zona_base + cols_zona_desc + cols_zona_geom
    polygons_final_cols = [c for c in polygons_final_cols if c in polygons_result.columns]
    
    polygons_result = polygons_result[polygons_final_cols]
    
    # Guardar archivo Excel de polígonos
    polygons_output_path = os.path.join(output_dir, 'zonas_para_google_maps.xlsx')
    polygons_result.to_excel(polygons_output_path, index=False)
    print(f"Archivo de zonas guardado en: {polygons_output_path}")

    # Continuar con el proceso original
    joined = gpd.sjoin(
        map_points,
        map_polygons,
        how='left',
        predicate='within',
        lsuffix='cliente',
        rsuffix='zona'
    )

    # Determina los nombres de columnas después del sjoin
    cliente_name_col = "Name_cliente"
    cliente_desc_col = "Description_cliente"
    cliente_geom_col = "geometry"
    zona_name_col = "Name_zona"
    zona_desc_col = "Description_zona"

    joined = joined.drop_duplicates(subset=[cliente_name_col, cliente_desc_col, cliente_geom_col])
    print("Columnas después del sjoin:", joined.columns)

    # Renombra columnas para claridad
    joined = joined.rename(columns={
        cliente_name_col: "cliente_name",
        cliente_desc_col: "cliente_description",
        cliente_geom_col: "cliente_geometry",
        zona_name_col: "zona_nombre",
        zona_desc_col: "zona_description",
    })

    # Asegura que existan las columnas de zona aunque sean None
    if "zona_nombre" not in joined.columns:
        joined["zona_nombre"] = None
    if "zona_description" not in joined.columns:
        joined["zona_description"] = None
    # No hay zona_geometry, así que créala como None
    joined["zona_geometry"] = None

    # Convierte geometría a WKT
    joined['cliente_geometry'] = joined['cliente_geometry'].apply(lambda g: g.wkt if pd.notnull(g) else None)

    # Expande las descripciones en columnas separadas
    cliente_desc_df = joined['cliente_description'].apply(parse_desc).apply(pd.Series)
    zona_desc_df = joined['zona_description'].apply(parse_desc).apply(pd.Series)

    # Prefijos para evitar colisiones de nombres
    if not cliente_desc_df.empty:
        cliente_desc_df = cliente_desc_df.add_prefix('cliente_')
    if not zona_desc_df.empty:
        zona_desc_df = zona_desc_df.add_prefix('zona_')

    # Selecciona solo las columnas que existen
    cols = [c for c in ['cliente_name', 'cliente_description', 'cliente_geometry', 'zona_nombre', 'zona_description', 'zona_geometry'] if c in joined.columns]
    joined_base = joined[cols].reset_index(drop=True)

    # Concatena todo
    result = pd.concat([
        joined_base,
        cliente_desc_df.reset_index(drop=True),
        zona_desc_df.reset_index(drop=True)
    ], axis=1)

    # Elimina las columnas de descripción originales si ya están expandidas
    result = result.drop(columns=['cliente_description', 'zona_description'])

    # Ordena columnas: cliente/zona básicos, luego expandidos
    cols_base = ['cliente_name', 'cliente_geometry', 'zona_nombre', 'zona_geometry']
    cols_cliente_exp = [c for c in result.columns if c.startswith('cliente_') and c not in cols_base]
    cols_zona_exp = [c for c in result.columns if c.startswith('zona_') and c not in cols_base]
    final_cols = ['cliente_name'] + cols_cliente_exp + ['cliente_geometry', 'zona_nombre'] + cols_zona_exp + ['zona_geometry']
    final_cols = [c for c in final_cols if c in result.columns]

    result = result[final_cols]

    output_path = os.path.join(output_dir, 'clientes_con_nuevazona.xlsx')
    result.to_excel(output_path, index=False)