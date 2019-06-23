from osgeo import gdal, ogr
import sys, os

def create_empty_shp(shp_path, geom_type, prj):
        
    driver = ogr.GetDriverByName("ESRI Shapefile")
    datasource = driver.CreateDataSource(shp_path)                                
        
    if geom_type == 'POLYGON':
        geom_typeshp = ogr.wkbPolygon
    elif geom_type == 'MULTILINESTRING':
        geom_typeshp = ogr.wkbMultiLineString
    elif geom_type == 'MULTIPOINT' or geom_type == 'POINT':
        geom_typeshp = ogr.wkbMultiPoint     
    else:
        print('Error. Unknown geometry type')
        sys.exit()

    layercr = datasource.CreateLayer(shp_path, prj, geom_typeshp, options = ['ENCODING=UTF-8'])
        
    layercr = None
    datasource = None
       
def write_fields_to_shp(shp_name, sxflayer):
        
    driver = ogr.GetDriverByName("ESRI Shapefile")
    shpsource = driver.Open(shp_name,1)
    shplayer = shpsource.GetLayer(0)
        
    sxfLayerDefn = sxflayer.GetLayerDefn()
        
    for i in range(0, sxfLayerDefn.GetFieldCount()):
        
        sxffieldDefn = sxfLayerDefn.GetFieldDefn(i)
        shplayer.CreateField(sxffieldDefn)

    shpLayerDefn = shplayer.GetLayerDefn()
    
    shplayer = None
    shpsource = None

def write_to_shp(inFeature, sxflayer, shp_name):

    driver = ogr.GetDriverByName("ESRI Shapefile")
    shpsource = driver.Open(shp_name,1)
    shplayer = shpsource.GetLayer()
        
    sxfLayerDefn = sxflayer.GetLayerDefn()
    shpLayerDefn = shplayer.GetLayerDefn()
            
    outFeature = ogr.Feature(shpLayerDefn)
    
    wktFeature = inFeature.GetGeometryRef().ExportToWkt()
    geomwkt = ogr.CreateGeometryFromWkt(wktFeature)
    outFeature.SetGeometry(geomwkt)
    
    for i in range(0, shpLayerDefn.GetFieldCount()):
        
        outFeature.SetField(shpLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
         
    #Добавляем объект в shp
    shplayer.CreateFeature(outFeature)
    
    inFeature, outFeature = None, None
    shplayer = None
    shpsource = None
    
    
    

gdal.PushErrorHandler('CPLQuietErrorHandler')

print('\n', 'Enter the sxf path (example: C:\work\Alyaska.sxf)')
sxf_name = str(input())
sxfsource = ogr.Open(sxf_name)

if sxfsource is None:
    print('\n', 'Error. Open failed')
    sys.exit()

print('\n','Enter the path for shp files (example: C:\work\exportshp\)')
shp_path = str(input())

if os.path.exists(shp_path) is False:
    print("\nError. Path for shp files doesn't exist")
    sys.exit()

metadata = sxfsource.GetMetadata()
print('\n', 'Metadata:', metadata, '\n')

layer_for_proj = sxfsource.GetLayer(0)
prj = layer_for_proj.GetSpatialRef()
del layer_for_proj

#вывод названий слоев и числа объектов в каждом из них

for i in range(sxfsource.GetLayerCount()):
    
    layer_show = sxfsource.GetLayer(i)
    layer_name = layer_show.GetName()
    layer_f_count = layer_show.GetFeatureCount()
    print(i+1, layer_name, 'Number of features =', layer_f_count)
    
    layer_show = None 

#создаем пустые shp файлы

for i in range(sxfsource.GetLayerCount()):
    
    #Получаем слой и его название
    geom_list=[]
    layer = sxfsource.GetLayer(i)
    layer_name = layer.GetName()
    error_count = 0    
    features_count = layer.GetFeatureCount()
    
    #Проверяем, какие типы геометрии есть в слое
    for _ in range(features_count):
            
        feature = layer.GetNextFeature() 
        
        if feature == None:
            error_count = error_count+1
        else:
            geometry = feature.GetGeometryRef()
            geom_name=geometry.GetGeometryName()
            
            if geom_name not in geom_list:
                geom_list.append(geom_name)
                
        feature = None
        
    #print('Number of errors in %s =' %layer_name, error_count)
    #print('Types of geometries:', geom_list)  
    
    multipointfile = False
    
    #Создаем соответствующие shp-файлы
    if 'POLYGON' in geom_list:
        poly_shp_name = '{shp_path}{layer_name}_polygon.shp'.format(shp_path = shp_path, layer_name = layer_name)
            
        create_empty_shp(poly_shp_name,'POLYGON',prj)
        write_fields_to_shp(poly_shp_name, layer)
            
    if 'MULTILINESTRING' in geom_list:
        line_shp_name = '{shp_path}{layer_name}_line.shp'.format(shp_path = shp_path, layer_name = layer_name)
        
        create_empty_shp(line_shp_name,'MULTILINESTRING',prj)
        write_fields_to_shp(line_shp_name, layer)
            
    if 'MULTIPOINT' in geom_list:
        point_shp_name = '{shp_path}{layer_name}_point.shp'.format(shp_path = shp_path, layer_name = layer_name)
   
        create_empty_shp(point_shp_name,'MULTIPOINT',prj) 
        write_fields_to_shp(point_shp_name, layer)
        
        multipointfile = True
    
    if 'POINT' in geom_list and multipointfile == False:
        point_shp_name = '{shp_path}{layer_name}_point.shp'.format(shp_path = shp_path, layer_name = layer_name)
   
        create_empty_shp(point_shp_name,'POINT',prj) 
        write_fields_to_shp(point_shp_name, layer)
    
    layer = None

#записываем объекты в созданные shp-файлы

for i in range(sxfsource.GetLayerCount()):
            
    layerw = sxfsource.GetLayer(i)
    layerw.ResetReading()
    layerw_name = layerw.GetName()
    print('\n', 'writing to %s ...' %layerw_name)   
    featuresw_count = layerw.GetFeatureCount()
    
    for _ in range(featuresw_count):  
        
        featurew = layerw.GetNextFeature()
        
        if featurew is None:
            print('\n', "Error. Feature of sxf layer is None")
            sys.exit()
        else:
            geometryw = featurew.GetGeometryRef()
            geom_name_feature = geometryw.GetGeometryName()
            
            poly_shp_name = '{shp_path}{layer_name}_polygon.shp'.format(shp_path = shp_path, layer_name = layerw_name)
            line_shp_name = '{shp_path}{layer_name}_line.shp'.format(shp_path = shp_path, layer_name = layerw_name)
            point_shp_name = '{shp_path}{layer_name}_point.shp'.format(shp_path = shp_path, layer_name = layerw_name)
            
            if geom_name_feature == 'POLYGON':
                write_to_shp(featurew, layerw, poly_shp_name)

            if geom_name_feature == 'MULTILINESTRING':
                 write_to_shp(featurew, layerw, line_shp_name)
            
            if geom_name_feature == 'MULTIPOINT':
                write_to_shp(featurew, layerw, point_shp_name)
                
            if geom_name_feature == 'POINT':
                write_to_shp(featurew, layerw, point_shp_name)
            
            featurew = None
    
    print('writing to %s finished' %layerw_name)
    
    layerw = None

print('\n',"Export finished!")

del sxfsource    