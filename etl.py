import requests,pandas,geopandas,matplotlib

# There are 80 sirens in Maui County, requesting higher OBJID numbers don't return anything
OBJID_RANGE = range(0,100)
objid_str_comma_sep = ','.join([str(x) for x in OBJID_RANGE])
objid_str_comma_sep

# These bounding box coordinates collected manually
MIN_LONG = -156.723355
MAX_LONG = -156.622007
MIN_LAT = 20.818488
MAX_LAT = 20.944385

GPS_COORDS = "epsg:4326"
MAUI_FOOT_CRS = "esri:102662"

params = {
    'f': 'json',
    'objectIds': objid_str_comma_sep,
    'outFields': 'Decibel,Island,Lat,Lon,Model,Name,POINT_X,POINT_Y,Range_ft,Siren,Solar,OBJECTID,GlobalID',
    'outSR': '102100',
    'returnM': 'true',
    'returnZ': 'true',
    'spatialRel': 'esriSpatialRelIntersects',
    'where': '1=1',
}

response = requests.get(
    'https://services3.arcgis.com/fsrDo0QMPlK9CkZD/arcgis/rest/services/Tsunami_Sirens/FeatureServer/0/query',
    params=params
)

maui_sirens = pandas.DataFrame(pandas.DataFrame(response.json()["features"])["attributes"].to_list())
print(f"{maui_sirens.shape[0]} sirens in the dataset")
print(str(maui_sirens[maui_sirens["Lat"].notna()].shape[0])+" sirens with coordinate info")
print(str(maui_sirens[maui_sirens["Range_ft"].notna()].shape[0])+" sirens with range info")
print("Sirens missing coordinate information:")
print(maui_sirens[(maui_sirens["Lat"].isna())|(maui_sirens["Lon"].isna())]["Name"].to_list())
print("(Manual review confirmed none of these are in the Lahaina burn perimeter)")

maui_sirens["dec_num"] = pandas.to_numeric(maui_sirens["Decibel"],errors="coerce")
maui_sirens["range_num"] = maui_sirens["Range_ft"].apply(lambda x: str(x).split(" ")[0])
maui_sirens["range_num"] = pandas.to_numeric(maui_sirens["range_num"], errors="coerce")

def in_bounding_coords(lat,long):
    lat = float(lat)
    long = float(long)
    if (lat >= MIN_LAT) & (lat <= MAX_LAT) & (long >= MIN_LONG) & (long <= MAX_LONG):
        return True
    return False

# Make a column that says whether the sirens are close to the burn perimeter
maui_sirens["near_bp"] = maui_sirens.apply(lambda x: in_bounding_coords(x["Lat"],x["Lon"]),axis=1)
print(str(maui_sirens[maui_sirens["near_bp"]].shape[0])+" sirens near the lahaina burn.")

maui_sirens_geo = geopandas.GeoDataFrame(maui_sirens, geometry=geopandas.points_from_xy(maui_sirens.Lon, maui_sirens.Lat))
maui_sirens_geo = maui_sirens_geo[maui_sirens_geo["Lat"]!=0]
# Set the CRS
maui_sirens_geo.crs = GPS_COORDS
maui_sirens_geo.to_file("data/processed/maui_sirens--coord_map.geojson")
maui_sirens_geo.plot()
matplotlib.pyplot.show()

maui_sirens_buff = maui_sirens_geo[maui_sirens_geo["range_num"] > 0]


# Change to a foot-based CRS to run the buffer 
maui_sirens_buff.to_crs(MAUI_FOOT_CRS, inplace=True)
maui_sirens_buff['geometry'] = maui_sirens_buff.apply(lambda x: x.geometry.buffer(x.range_num), axis=1)

# Change CRS back
maui_sirens_buff.to_crs(GPS_COORDS, inplace=True)
maui_sirens_buff.plot()
matplotlib.pyplot.show()

maui_sirens_buff.to_file("data/processed/maui_sirens--buffer.geojson")