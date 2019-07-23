import argparse
import os
import math
import pathlib
import time
from osgeo import gdal, ogr, osr


class GridBuilder:
    """
    Methods to clip shapefile by scale grid.
    """

    def __init__(self,
                 crs: osr.SpatialReference,
                 extent: tuple,
                 scale: int,
                 driver=ogr.GetDriverByName("ESRI Shapefile")):
        """
        :param crs: Source CRS: osr.SpatialReference.
        :param extent: Polygonal extent of shapefile with 2 coordinates (upper-left, lower-right): tuple.
        :param scale: Scale denominator [1000000, 100000, 50000, 25000]: int.
        :param driver: Driver for vector layer: osgeo.ogr object
        """
        self.crs = crs
        self.extent = extent
        self.scale = scale
        self.step_x = Nomenklatura.scales(scale)[0]
        self.step_y = Nomenklatura.scales(scale)[1]
        self.driver = driver
        self.proj4 = "+proj=longlat +datum=WGS84 +no_defs"

    def grid_points(self):
        """
        Generator. Calculate coordinates of each polygon for your grid.
        x1y1-----x2y2
        |          |
        |          |
        |          |
        x4y4-----x3y3
        return: Generator
        """

        extent_x1, extent_y1 = self.reproject_point(self.crs, self.extent[0], self.extent[3])
        extent_x2, extent_y2 = self.reproject_point(self.crs, self.extent[1], self.extent[2])

        x_start = (extent_x1 // self.step_x) * self.step_x
        y_start = (extent_y1 // self.step_y) * self.step_y + self.step_y
        x_end = (extent_x2 // self.step_x) * self.step_x + self.step_x
        y_end = (extent_y2 // self.step_y) * self.step_y

        print('grid boundary: ', x_start, y_start, x_end, y_end)

        _x, _y = x_start, y_start

        while _x <= x_end and _y > y_end:
            x1, y1 = _x, _y
            x2, y2 = _x + self.step_x, _y
            x3, y3 = _x + self.step_x, _y - self.step_y
            x4, y4 = _x, _y - self.step_y

            if _x + self.step_x > x_end:
                _x, _y = x_start, _y - self.step_y
            else:
                _x = _x + self.step_x
                yield x1, y1, x2, y2, x3, y3, x4, y4

    @staticmethod
    def polygon(x1, y1, x2, y2, x3, y3, x4, y4):
        """
        Create polygon geometry by coordinates.
        return: ogr.Geometry
        """

        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(x1, y1)
        ring.AddPoint(x2, y2)
        ring.AddPoint(x3, y3)
        ring.AddPoint(x4, y4)
        ring.AddPoint(x1, y1)

        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        return poly

    def reproject(self, source_crs, geometry):
        """
        Reproject geometry from source CRS to geographic coordinates (EPSG:4284 Pulkovo 1942)
        :param source_crs:
        :param geometry:
        :return: ogr.Geometry
        """
        target_crs = osr.SpatialReference()
        target_crs.ImportFromProj4(self.proj4)

        transform = osr.CoordinateTransformation(source_crs, target_crs)
        geometry.Transform(transform)

        return geometry

    def reproject_point(self, source_crs, x, y):
        """
        Reproject x, y from source CRS to geographic coordinates (EPSG:4284 Pulkovo 1942)
        :param source_crs:
        :param geometry:
        :return: x, y: float
        """

        target_crs = osr.SpatialReference()
        target_crs.ImportFromProj4(self.proj4)

        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
        transform = osr.CoordinateTransformation(source_crs, target_crs)
        point.Transform(transform)

        return point.GetX(), point.GetY()

    def create_empty_shp(self, path, geometry=ogr.wkbPolygon, nom_field=False):
        """
        Create empty shapefile.
        :param path: Path to create empty shapefile: str.
        :param geometry: Type of geometry: ogr object.
        :param nom_field: Write field "Razgraphka" or not to empty shapefile: bool.
        return: shapefile.
        """
        if geometry == ogr.wkbMultiPoint:
            geometry = ogr.wkbPoint

        if os.path.exists(os.path.dirname(path)):
            datasource = self.driver.CreateDataSource(path)
            target_crs = osr.SpatialReference()
            target_crs.ImportFromProj4(self.proj4)
            layer = datasource.CreateLayer('grid_layer', target_crs, geometry, options=['ENCODING=UTF-8'])
        else:
            raise ValueError("Path doesn't exist")

        if nom_field:
            field_name = ogr.FieldDefn("Razgraphka", ogr.OFTString)
            field_name.SetWidth(24)
            layer.CreateField(field_name)

        del layer
        del datasource

    def create_grid(self, path):
        """
        Create grid shapefile for source shapefile with your scale denominator.
        :param path: Path for grid-shapefile: str.
        :return: shapefile.
        """

        self.create_empty_shp(path, nom_field=True)
        source = self.driver.Open(path, 1)
        layer = source.GetLayer()

        for grid_poly in self.grid_points():
            name = Nomenklatura((grid_poly[0]+grid_poly[4])/2, (grid_poly[1]+grid_poly[5])/2)
            namelist = name.get_nomenklatura(self.scale)

            featureDefn = layer.GetLayerDefn()
            feature = ogr.Feature(featureDefn)
            feature.SetGeometry(self.polygon(*grid_poly))
            feature.SetField("Razgraphka", namelist[0])
            layer.CreateFeature(feature)
            del feature

        del layer
        del source

    def __intersection_to_file(self, grid_path, shp_path, target_path):
        grid_source = self.driver.Open(grid_path, 1)
        grid_layer = grid_source.GetLayer()

        shp_source = self.driver.Open(shp_path, 1)
        shp_layer = shp_source.GetLayer()
        shp_geom_type = shp_layer.GetGeomType()

        self.create_empty_shp(target_path, geometry=shp_geom_type)
        target_source = self.driver.Open(target_path, 1)
        target_layer = target_source.GetLayer()

        for feature1 in grid_layer:
            geom1 = feature1.GetGeometryRef()
            attribute1 = feature1.GetField('Razgraphka')
            for feature2 in shp_layer:
                geom2 = feature2.GetGeometryRef()
                if geom1.Intersect(geom2):
                    intersection = geom2.Intersection(geom1)
                    dstfeature = ogr.Feature(target_layer.GetLayerDefn())
                    dstfeature.SetGeometry(intersection)
                    dstfeature.SetField('Razgraphka', attribute1)
                    target_layer.CreateFeature(dstfeature)
                    del dstfeature
            shp_layer.ResetReading()

        del grid_source, shp_source, target_source, grid_layer, shp_layer, target_layer

    def intersection_to_dirs(self, grid_path, shp_path, target_path):
        """
        Create shapefiles for each grid cell and move it to named 'Nomenklatura' folders.
        :param grid_path: Path of grid to clip source shapefile: str.
        :param shp_path: Path of source shapefile to clip: str.
        :param target_path: Path of directory for new clipped shapefiles: str.
        :return: clipped shapefiles in named folders.
        """

        grid_source = self.driver.Open(grid_path, 1)
        grid_layer = grid_source.GetLayer()

        shp_source = self.driver.Open(shp_path, 1)
        shp_layer = shp_source.GetLayer()
        shp_crs = shp_layer.GetSpatialRef()
        shp_geom_type = shp_layer.GetGeomType()

        for feature1 in grid_layer:
            geom1 = feature1.GetGeometryRef()
            attribute1 = feature1.GetField('Razgraphka')
            for feature2 in shp_layer:
                geom2 = self.reproject(shp_crs, feature2.GetGeometryRef())
                if geom1.Intersect(geom2):
                    intersection = geom2.Intersection(geom1)

                    path = pathlib.Path(target_path)
                    target_dir = path / attribute1
                    if not target_dir.is_dir():
                        target_dir.mkdir(parents=True, exist_ok=True)

                    target_shp_dir = target_dir / str(attribute1+'_'+os.path.basename(shp_path))

                    if not os.path.exists(str(target_shp_dir)):
                        print(str(target_shp_dir))
                        self.create_empty_shp(str(target_shp_dir),
                                              geometry=shp_geom_type)

                        target_source = self.driver.Open(str(target_shp_dir), 1)
                        target_layer = target_source.GetLayer()

                        shp_layer_defn = shp_layer.GetLayerDefn()
                        for i in range(0, shp_layer_defn.GetFieldCount()):
                            field_defn = shp_layer_defn.GetFieldDefn(i)
                            target_layer.CreateField(field_defn)
                    else:
                        target_source = self.driver.Open(str(target_shp_dir), 1)
                        target_layer = target_source.GetLayer()

                    layer_defn = target_layer.GetLayerDefn()
                    dstfeature = ogr.Feature(layer_defn)
                    dstfeature.SetGeometry(intersection)

                    for i in range(layer_defn.GetFieldCount()):
                        dstfeature.SetField(layer_defn.GetFieldDefn(i).GetNameRef() , feature2.GetField(i))
                    target_layer.CreateFeature(dstfeature)

                    del dstfeature, target_layer, target_source

            shp_layer.ResetReading()

        del grid_source, shp_source, grid_layer, shp_layer

    @classmethod
    def get_shapes_by_grid(cls, scale, source_path, target_dir):
        """
        Common method to create new clipped and named shapefiles by source shapefile and scale grid.
        :param scale: Scale denominator [1000000, 100000, 50000, 25000]
        :param source_path: Path of source shapefile - str.
        :param target_dir: Directory path for new shapefiles - str.
        :return: clipped shapefiles in named folders.
        """
        gdal.PushErrorHandler('CPLQuietErrorHandler')

        driver = ogr.GetDriverByName("ESRI Shapefile")

        source = driver.Open(source_path)
        layer = source.GetLayer()
        crs = layer.GetSpatialRef()
        extent = layer.GetExtent()

        grid = GridBuilder(crs=crs, extent=extent, scale=scale)
        grid_name = 'grid' + str(scale) + '.shp'
        grid_path = os.path.join(target_dir, grid_name)

        grid.create_grid(grid_path)
        grid.intersection_to_dirs(grid_path, source_path, target_dir)


class Nomenklatura:
    """
    Methods to create special names by russian mapping scale series.
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def scales(cls, scale):
        """
        Grid steps for each scale - {scale : (step_for_longitude, step_for_latitude)}
        :param scale: int
        :return: tuple.
        """

        SCALES = {1000000: (6, 4),
                   100000: (30/60, 20/60),
                    50000: (15/60, 10/60),
                    25000: (7.5/60, 5/60)}

        return SCALES[scale]

    def get_nomenklatura(self, scale):
        """
        Get method to create name for grid polygon by your scale.
        :param scale: int
        :return: func.
        """

        scale_method = {1000000: self.m_1mln(),
                  100000: self.m_100k(),
                  50000: self.m_50k(),
                  25000: self.m_25k()}
        return scale_method[scale]

    def m_1mln(self):
        """
        Create names for polygons in 1 : 1 000 000
        :return: Name for polygon and its boundary: list
        """

        storage_1mln = { 0: 'A',
                         1: 'B',
                         2: 'C',
                         3: 'D',
                         4: 'E',
                         5: 'F',
                         6: 'G',
                         7: 'H',
                         8: 'I',
                         9: 'J',
                        10: 'K',
                        11: 'L',
                        12: 'M',
                        13: 'N',
                        14: 'O',
                        15: 'P',
                        16: 'Q',
                        17: 'R',
                        18: 'S',
                        19: 'T',
                        20: 'U',
                        21: 'V',
                        22: 'Z'}

        y_1mln = math.fabs(self.y // 4)
        x_1mln = (180 + self.x) // 6 + 1

        list_boundary = (self.x // 6 * 6,
                         self.y // 4 * 4 + 4,
                         self.x // 6 * 6 + 6,
                         self.y // 4 * 4)

        return ['{}-{}'.format(storage_1mln[y_1mln], int(x_1mln)), list_boundary]

    def m_100k(self):
        """
        Create names for polygons in 1 : 100 000
        :return: Name for polygon and its boundary: list
        """

        name_1mln, boundary = self.m_1mln()

        y_line = (boundary[1]-self.y) // (20/60)
        x_line = (self.x-boundary[0]) // (30/60)
        n = (y_line * 12 + 1) + x_line

        list_boundary = (self.x // (30/60) * (30/60),
                         self.y // (20/60) * (20/60) + (20/60),
                         self.x // (30/60) * (30/60) + (30/60),
                         self.y // (20/60) * (20/60))

        return ['{}-{}'.format(name_1mln, int(n)), list_boundary]

    def m_50k(self):
        """
        Create names for polygons in 1 : 50 000
        :return: Name for polygon and its boundary: list
        """

        name_100k, boundary = self.m_100k()

        mid_x = (boundary[2] + boundary[0]) / 2
        mid_y = (boundary[3] + boundary[1]) / 2

        if self.x < mid_x and self.y > mid_y:
            litera = 'A'
        elif self.x > mid_x and self.y > mid_y:
            litera = 'Б'
        elif self.x < mid_x and self.y < mid_y:
            litera = 'В'
        elif self.x > mid_x and self.y < mid_y:
            litera = 'Г'
        else:
            litera = '?'

        list_boundary = (self.x // (15 / 60) * (15 / 60),
                         self.y // (10 / 60) * (10 / 60) + (10 / 60),
                         self.x // (15 / 60) * (15 / 60) + (15 / 60),
                         self.y // (10 / 60) * (10 / 60))

        return ['{}-{}'.format(name_100k, litera), list_boundary]

    def m_25k(self):
        """
        Create names for polygons in 1 : 25 000
        :return: Name for polygon and its boundary: list
        """

        name_50k, boundary = self.m_50k()

        mid_x = (boundary[2] + boundary[0]) / 2
        mid_y = (boundary[3] + boundary[1]) / 2

        if self.x < mid_x and self.y > mid_y:
            litera = 'а'
        elif self.x > mid_x and self.y > mid_y:
            litera = 'б'
        elif self.x < mid_x and self.y < mid_y:
            litera = 'в'
        elif self.x > mid_x and self.y < mid_y:
            litera = 'г'
        else:
            litera = '?'

        list_boundary = (self.x // (7.5 / 60) * (7.5 / 60),
                         self.y // (5 / 60) * (5 / 60) + (5 / 60),
                         self.x // (7.5 / 60) * (7.5 / 60) + (7.5 / 60),
                         self.y // (5 / 60) * (5 / 60))

        return ['{}-{}'.format(name_50k, litera), list_boundary]


def main():
    """
    Main function for command line utility. 3 required arguments - -scale, -shp, -out.
    :return: result.
    """

    def arguments():
        parser = argparse.ArgumentParser(description='Utility for clipping shapefile by scale grid')
        parser.add_argument('-scale',
                            required=True, nargs='+',
                            help='Scale denominator [1000000, 100000, 50000, 25000].')
        parser.add_argument('-shp',
                            required=True, nargs='+',
                            help='Path to source shapefile.')
        parser.add_argument('-out',
                            required=True, nargs='+',
                            help='Directory to export clipped shapefiles')
        try:
            p = parser.parse_args()
        except Exception:
            p.print_help()
            p.print_usage()
            return

        return [p.scale, p.shp, p.out]

    scale, shp, out_directory = arguments()
    cur_time = time.time()

    if os.path.splitext(shp[0])[1] == '.shp':
        GridBuilder.get_shapes_by_grid(int(scale[0]),
                                       str(shp[0]),
                                       str(out_directory[0]))
    elif not os.path.splitext(shp[0])[1]:
        files = os.listdir(shp[0])
        for file in files:
            if os.path.splitext(file)[1] == '.shp':
                GridBuilder.get_shapes_by_grid(int(scale[0]),
                                               str(os.path.join(shp[0], file)),
                                               str(out_directory[0]))

    print('Process time:', round(time.time() - cur_time, 2), 'sec')


if __name__ == '__main__':
    main()