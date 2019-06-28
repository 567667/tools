import os
import math
from osgeo import ogr, osr

import time


class GridBuilder:
    def __init__(self,
                 prj: osr.SpatialReference,
                 extent: tuple,
                 scale: int,
                 driver=ogr.GetDriverByName("ESRI Shapefile")):
        self.prj = prj
        self.extent = extent
        self.scale = scale
        self.step_x = Nomenklatura.scales(scale)[0]
        self.step_y = Nomenklatura.scales(scale)[1]
        self.driver = driver

    def grid_points(self):
        """
        Calculate coordinates of polygons for GRID.
        x1y1-----x2y2
        |          |
        |          |
        |          |
        x4y4-----x3y3
        """
        x1, y1 = self.extent[0], self.extent[3]
        x2, y2 = self.extent[1], self.extent[2]

        x_start = (x1 // self.step_x) * self.step_x
        y_start = (y1 // self.step_y) * self.step_y + self.step_y
        x_end = (x2 // self.step_x) * self.step_x + self.step_x
        y_end = (y2 // self.step_y) * self.step_y + self.step_y

        print('grid boundary: ', x_start, y_start, x_end, y_end)

        _x, _y = x_start, y_start

        while _x <= x_end and _y >= y_end:
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

    def create_empty_shp(self, path, prj, geometry=ogr.wkbPolygon):
        if os.path.exists(os.path.dirname(path)):
            datasource = self.driver.CreateDataSource(path)
            layer = datasource.CreateLayer('grid_layer', prj, geometry, options=['ENCODING=UTF-8'])
        else:
            raise ValueError("Path doesn't exist")

        field_name = ogr.FieldDefn("Name", ogr.OFTString)
        field_name.SetWidth(24)
        layer.CreateField(field_name)

        del layer
        del datasource

    def create_grid(self, path):
        self.create_empty_shp(path, self.prj)
        source = self.driver.Open(path, 1)
        layer = source.GetLayer()

        for grid_poly in self.grid_points():
            name = Nomenklatura((grid_poly[0]+grid_poly[4])/2, (grid_poly[1]+grid_poly[5])/2)
            namelist = name.get_nomenklatura(self.scale)

            featureDefn = layer.GetLayerDefn()
            feature = ogr.Feature(featureDefn)
            feature.SetGeometry(self.polygon(*grid_poly))
            feature.SetField("Name", namelist[0])
            layer.CreateFeature(feature)
            del feature

        del layer
        del source

    def intersection(self, grid_path, shp_path, target_path):
        grid_source = self.driver.Open(grid_path, 1)
        grid_layer = grid_source.GetLayer()

        shp_source = self.driver.Open(shp_path, 1)
        shp_layer = shp_source.GetLayer()
        shp_geom_type = shp_layer.GetGeomType()

        self.create_empty_shp(target_path, self.prj, geometry=shp_geom_type)
        target_source = self.driver.Open(target_path, 1)
        target_layer = target_source.GetLayer()

        for feature1 in grid_layer:
            geom1 = feature1.GetGeometryRef()
            attribute1 = feature1.GetField('Name')
            for feature2 in shp_layer:
                geom2 = feature2.GetGeometryRef()
                if geom1.Intersect(geom2):
                    intersection = geom2.Intersection(geom1)
                    dstfeature = ogr.Feature(target_layer.GetLayerDefn())
                    dstfeature.SetGeometry(intersection)
                    dstfeature.SetField('Name', attribute1)
                    target_layer.CreateFeature(dstfeature)
                    del dstfeature
            shp_layer.ResetReading()

        del grid_source, shp_source, target_source, grid_layer, shp_layer, target_layer


class Nomenklatura:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def scales(cls, scale):
        SCALES = {1000000: (6,4),
                   100000: (30/60, 20/60),
                    50000: (15/60, 10/60),
                    25000: (7.5/60, 5/60)}

        return SCALES[scale]

    def get_nomenklatura(self, scale):
        scale_method = {1000000: self.m_1mln(),
                  100000: self.m_100k(),
                  50000: self.m_50k(),
                  25000: self.m_25k()}
        return scale_method[scale]

    def m_1mln(self):
        storage_1mln = {0: 'A',
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
        #if self.y % 4 == 0:
        #    y_1mln -= 1
        x_1mln = (180 + self.x) // 6 + 1

        list_boundary = (self.x // 6 * 6,
                         self.y // 4 * 4 + 4,
                         self.x // 6 * 6 + 6,
                         self.y // 4 * 4)

        return ['{}-{}'.format(storage_1mln[y_1mln], int(x_1mln)), list_boundary]

    def m_100k(self):
        name_1mln, boundary = self.m_1mln()

        y_line = (boundary[1]-self.y) // (20/60)
        x_line = (self.x-boundary[0]) // (30/60)
        n = (y_line * 12 + 1) + x_line

        list_boundary = (self.x // (30/60) * (30/60),
                         self.y // (20/60) * (20/60) + (20/60),
                         self.x // (30/60) * (30/60) + (30/60),
                         self.y // (20/60) * (20/60))

        #print(self.x, self.y, '{}-{}'.format(name_1mln, int(n)))
        return ['{}-{}'.format(name_1mln, int(n)), list_boundary]

    def m_50k(self):
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


def test_grid():
    driver = ogr.GetDriverByName("ESRI Shapefile")
    source = driver.Open(r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\poly_wgs84.shp")
    layer = source.GetLayer()
    prj = layer.GetSpatialRef()
    extent = layer.GetExtent()

    grid = GridBuilder(prj=prj, extent=extent, scale=25000)

    path = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\testing\setka.shp"
    grid.create_grid(path)


def test_intersection():
    driver = ogr.GetDriverByName("ESRI Shapefile")
    shppath = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\poly_wgs84.shp"
    source = driver.Open(shppath)
    layer = source.GetLayer()
    prj = layer.GetSpatialRef()
    extent = layer.GetExtent()

    grid = GridBuilder(prj=prj, extent=extent, scale=25000)

    path = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\testing\setka.shp"

    inter = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\testing\inter.shp"

    grid.create_grid(path)
    grid.intersection(path, shppath, inter)

def test_vocab():
    print(Nomenklatura.scales(1000000))


if __name__ == '__main__':
    cur_time = time.time()
    test_intersection()
    print('Process time:', time.time() - cur_time)