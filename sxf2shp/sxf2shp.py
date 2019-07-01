import argparse
import os
from osgeo import gdal, ogr


class SxfExporter:
    def __init__(self,
                 sxf: str,
                 shp_dir: str,
                 driver=ogr.GetDriverByName("ESRI Shapefile")):
        self.sxf = sxf
        self.shp_dir = shp_dir
        self.driver = driver

    def create_empty_shp(self, shp_path, geom_type, prj):

        datasource = self.driver.CreateDataSource(shp_path)

        if geom_type == 'POLYGON':
            geom_typeshp = ogr.wkbPolygon
        elif geom_type == 'MULTILINESTRING':
            geom_typeshp = ogr.wkbMultiLineString
        elif geom_type == 'MULTIPOINT' or geom_type == 'POINT':
            geom_typeshp = ogr.wkbMultiPoint
        else:
            raise AttributeError('Error. Unknown geometry type')

        datasource.CreateLayer(shp_path, prj, geom_typeshp, options=['ENCODING=UTF-8'])

    def write_fields_to_shp(self, source_shp, sxflayer):
        source = self.driver.Open(source_shp, 1)
        shplayer = source.GetLayer()

        sxfLayerDefn = sxflayer.GetLayerDefn()

        for i in range(0, sxfLayerDefn.GetFieldCount()):
            sxffieldDefn = sxfLayerDefn.GetFieldDefn(i)
            shplayer.CreateField(sxffieldDefn)

    def write_to_shp(self, inFeature, shp_name):
        shpsource = self.driver.Open(shp_name, 1)
        shplayer = shpsource.GetLayer()

        shpLayerDefn = shplayer.GetLayerDefn()

        outFeature = ogr.Feature(shpLayerDefn)

        wktFeature = inFeature.GetGeometryRef().ExportToWkt()
        geomwkt = ogr.CreateGeometryFromWkt(wktFeature)
        outFeature.SetGeometry(geomwkt)

        for i in range(0, shpLayerDefn.GetFieldCount()):
            outFeature.SetField(shpLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))

        shplayer.CreateFeature(outFeature)

        del shpsource

    def get_metadata(self, sxfsource):
        layer_for_proj = sxfsource.GetLayer(0)
        prj = layer_for_proj.GetSpatialRef()

        metadata = sxfsource.GetMetadata()
        print('\n', 'Metadata:', metadata, '\n')

        for i in range(sxfsource.GetLayerCount()):
            layer_show = sxfsource.GetLayer(i)
            layer_name = layer_show.GetName()
            layer_f_count = layer_show.GetFeatureCount()
            print(i + 1, layer_name, 'Number of features =', layer_f_count)

        return prj

    def shp_creator(self, sxfsource, prj):
        for i in range(sxfsource.GetLayerCount()):

            # Получаем слой и его название
            geom_list = []
            layer = sxfsource.GetLayer(i)
            layer_name = layer.GetName()

            error_count = 0
            features_count = layer.GetFeatureCount()

            # Проверяем, какие типы геометрии есть в слое
            for _ in range(features_count):

                feature = layer.GetNextFeature()

                if not feature:
                    error_count = error_count + 1
                else:
                    geometry = feature.GetGeometryRef()
                    geom_name = geometry.GetGeometryName()

                    if geom_name not in geom_list:
                        geom_list.append(geom_name)

            multipointfile = False
            # Создаем соответствующие shp-файлы
            if 'POLYGON' in geom_list:
                poly_shp_name = '{layer_name}_polygon.shp'.format(layer_name=layer_name)

                self.create_empty_shp(os.path.join(self.shp_dir, poly_shp_name), 'POLYGON', prj)
                self.write_fields_to_shp(os.path.join(self.shp_dir, poly_shp_name), layer)

            if 'MULTILINESTRING' in geom_list:
                line_shp_name = '{layer_name}_line.shp'.format(layer_name=layer_name)

                self.create_empty_shp(os.path.join(self.shp_dir, line_shp_name), 'MULTILINESTRING', prj)
                self.write_fields_to_shp(os.path.join(self.shp_dir, line_shp_name), layer)

            if 'MULTIPOINT' in geom_list:
                point_shp_name = '{layer_name}_point.shp'.format(layer_name=layer_name)

                self.create_empty_shp(os.path.join(self.shp_dir, point_shp_name), 'MULTIPOINT', prj)
                self.write_fields_to_shp(os.path.join(self.shp_dir, point_shp_name), layer)

                multipointfile = True

            if 'POINT' in geom_list and multipointfile == False:
                point_shp_name = '{layer_name}_point.shp'.format(layer_name=layer_name)

                self.create_empty_shp(os.path.join(self.shp_dir, point_shp_name), 'POINT', prj)
                self.write_fields_to_shp(os.path.join(self.shp_dir, point_shp_name), layer)

    def write_features_to_shp(self, sxfsource):
        for i in range(sxfsource.GetLayerCount()):

            layerw = sxfsource.GetLayer(i)
            layerw.ResetReading()
            layerw_name = layerw.GetName()
            print('\n', 'writing to %s ...' % layerw_name)
            featuresw_count = layerw.GetFeatureCount()

            for _ in range(featuresw_count):

                featurew = layerw.GetNextFeature()

                if featurew is None:
                    print('\n', "Error. Feature of sxf layer is None")
                    return
                else:
                    geometryw = featurew.GetGeometryRef()
                    geom_name_feature = geometryw.GetGeometryName()

                    poly_shp_name = '{layer_name}_polygon.shp'.format(layer_name=layerw_name)
                    line_shp_name = '{layer_name}_line.shp'.format(layer_name=layerw_name)
                    point_shp_name = '{layer_name}_point.shp'.format(layer_name=layerw_name)

                    if geom_name_feature == 'POLYGON':
                        self.write_to_shp(featurew, os.path.join(self.shp_dir, poly_shp_name))

                    if geom_name_feature == 'MULTILINESTRING':
                        self.write_to_shp(featurew, os.path.join(self.shp_dir, line_shp_name))

                    if geom_name_feature == 'MULTIPOINT':
                        self.write_to_shp(featurew, os.path.join(self.shp_dir, point_shp_name))

                    if geom_name_feature == 'POINT':
                        self.write_to_shp(featurew, os.path.join(self.shp_dir, point_shp_name))

            print('writing to %s finished' % layerw_name)

    def convert(self):
        gdal.PushErrorHandler('CPLQuietErrorHandler')
        sxfsource = ogr.Open(self.sxf)

        if sxfsource is None:
            raise ValueError('Error. Open failed')

        if not os.path.exists(self.shp_dir):
            raise ValueError("\nError. Path for shp files doesn't exist")

        prj = self.get_metadata(sxfsource)
        self.shp_creator(sxfsource, prj)
        self.write_features_to_shp(sxfsource)

        del sxfsource


def main():
    def arguments():
        parser = argparse.ArgumentParser(description='Export SXF to SHP')
        parser.add_argument('-sxf',
                            required=True, nargs='+',
                            help='Path to SXF')
        parser.add_argument('-out',
                            required=True, nargs='+',
                            help='Directory for exported shapefiles')
        try:
            p = parser.parse_args()
        except Exception:
            return

        return [p.sxf, p.out]

    sxf, out_shp = arguments()
    project = SxfExporter(sxf=sxf[0], shp_dir=out_shp[0])
    project.convert()


if __name__ == '__main__':
    main()






