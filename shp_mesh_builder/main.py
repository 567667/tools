import os
from osgeo import ogr, gdal

gdal.PushErrorHandler('CPLQuietErrorHandler')


def grid_points(x1, y1, x2, y2, step_x, step_y):
    '''
    Calculate coordinates of points for GRID
    :param x1:
    :param y1:
    :param x2:
    :param y2:
    :param step_x:
    :param step_y:
    :return: tuple

    x1y1-----x2y2
    |          |
    |          |
    |          |
    x4y4-----x3y3

    '''

    x_start = (x1 // step_x) * step_x
    y_start = (y1 // step_y) * step_y
    x_end = (x2 // step_x) * step_x + step_x
    y_end = (y2 // step_y) * step_y + step_y

    print('grid boundary: ', x_start, y_start, x_end, y_end)

    _x, _y = x_start, y_start

    while _x <= x_end and _y >= y_end:
        x1, y1 = _x, _y
        x2, y2 = _x + step_x, _y
        x3, y3 = _x + step_x, _y - step_y
        x4, y4 = _x, _y - step_y

        if _x + step_x == x_end:
            _x, _y = x_start, _y - step_y
        else:
            _x = _x + step_x
            yield x1, y1, x2, y2, x3, y3, x4, y4


def create_shp(path, name, prj, writeobj=None, geometry=ogr.wkbPolygon):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(path):
        datasource = driver.CreateDataSource(os.path.join(path, name))
        layer = datasource.CreateLayer(name, prj, geometry, options=['ENCODING=UTF-8'])
    else:
        print("Path doesn't exist")
        return

    if writeobj is not None:
        # Add the fields we're interested in
        field_name = ogr.FieldDefn("Name", ogr.OFTString)
        field_name.SetWidth(24)
        layer.CreateField(field_name)

        # create the feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(writeobj)
        layer.CreateFeature(feature)
        del feature
        del datasource
        return


def import_shp(shapefile):
    driver = ogr.GetDriverByName("ESRI Shapefile")

    shpsource = driver.Open(shapefile, 1)
    layer = shpsource.GetLayer()
    extent = layer.GetExtent()
    prj = layer.GetSpatialRef()

    return [layer, extent, prj]


def polygon(x1, y1, x2, y2, x3, y3, x4, y4):
    # Create ring
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(x1, y1)
    ring.AddPoint(x2, y2)
    ring.AddPoint(x3, y3)
    ring.AddPoint(x4, y4)

    # Create polygon #1
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly


def main():
    shp = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\poly_wgs84.shp"
    newshp = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\testing"

    shp = import_shp(shp)
    print(shp)

    create_shp(
        r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\testing",
        'create1.shp',
        shp[2],
        writeobj=True
    )


def test_main():
    shp = r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\poly_wgs84.shp"
    driver = ogr.GetDriverByName("ESRI Shapefile")
    shp = driver.Open(shp)
    layer = shp.GetLayer()
    prj = layer.GetSpatialRef()
    extent = layer.GetExtent()
    multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)
    for grid_poly in grid_points(extent[0], extent[3], extent[1], extent[2], step_x=10, step_y=10):
        multipolygon.AddGeometry(polygon(*grid_poly))

    create_shp(r"C:\Users\kotov\Documents\github_kot\swd\shp_mesh_builder\data\testing",
               'newshp.shp',
               prj,
               writeobj=multipolygon,
               geometry=ogr.wkbPolygon)
    del shp
    del multipolygon


if __name__ == '__main__':
    test_main()
