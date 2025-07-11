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

    joined = gpd.sjoin(
        map_points,
        map_polygons,
        how='left',
        predicate='within',
        lsuffix='point',
        rsuffix='polygon'
    )

    point_name_col = f"{name_col}_point" if f"{name_col}_point" in joined.columns else name_col
    point_desc_col = f"{desc_col}_point" if f"{desc_col}_point" in joined.columns else desc_col
    point_geom_col = f"{geom_col}_point" if f"{geom_col}_point" in joined.columns else geom_col
    poly_name_col = f"{name_col}_polygon" if f"{name_col}_polygon" in joined.columns else (f"{name_col}_right" if f"{name_col}_right" in joined.columns else name_col)
    poly_desc_col = f"{desc_col}_polygon" if f"{desc_col}_polygon" in joined.columns else (f"{desc_col}_right" if f"{desc_col}_right" in joined.columns else desc_col)
    poly_geom_col = f"{geom_col}_polygon" if f"{geom_col}_polygon" in joined.columns else (f"{geom_col}_right" if f"{geom_col}_right" in joined.columns else geom_col)
    
    joined = joined.drop_duplicates(subset=[point_name_col, point_desc_col, point_geom_col])

    # Renombra columnas para claridad
    joined = joined.rename(columns={
        point_name_col: "Cliente_Nombre",
        point_desc_col: "Cliente_Descripcion",
        poly_name_col: "Zona_Nombre",
        poly_desc_col: "Zona_Descripcion",
        point_geom_col: "Cliente_Geometry",
        poly_geom_col: "Zona_Geometry",
    })

    if "Zona_Nombre" not in joined.columns:
        joined["Zona_Nombre"] = None
    if "Zona_Descripcion" not in joined.columns:
        joined["Zona_Descripcion"] = None

    # Aplica parse_desc a la descripción del cliente y del polígono y expande a columnas
    desc_cliente_df = joined['Cliente_Descripcion'].apply(parse_desc).apply(pd.Series)
    desc_poligono_df = joined['Zona_Descripcion'].apply(parse_desc).apply(pd.Series)

    desc_cliente_df = desc_cliente_df.add_prefix('Cliente_')
    desc_poligono_df = desc_poligono_df.add_prefix('Zona_')

    # Convierte geometrías a WKT
    joined['Cliente_Geometry'] = joined['Cliente_Geometry'].apply(lambda g: g.wkt if pd.notnull(g) else None)
    joined['Zona_Geometry'] = joined['Zona_Geometry'].apply(lambda g: g.wkt if pd.notnull(g) else None)

    result = pd.concat([joined.reset_index(drop=True), desc_cliente_df, desc_poligono_df], axis=1)

    columnas_finales = (
        ['Cliente_Nombre', 'Zona_Nombre']
        + list(desc_cliente_df.columns)
        + list(desc_poligono_df.columns)
        + ['Cliente_Geometry', 'Zona_Geometry']
    )
    result = result[columnas_finales]

    output_path = os.path.join(output_dir, 'clientes_con_nuevazona.xlsx')
    result.to_excel(output_path, index=False)