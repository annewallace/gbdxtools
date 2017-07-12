from __future__ import print_function
from functools import partial
from collections import Container
import os
import math

from shapely import wkt, ops
from shapely.geometry import box, shape, mapping
from shapely.geometry.base import BaseGeometry

import numpy as np
import pyproj

from gbdxtools.images.meta import DaskMeta, DaskImage, GeoImage
from gbdxtools.ipe.util import RatPolyTransform, AffineTransform
from gbdxtools.ipe.io import to_geotiff


class IpeImage(DaskImage, GeoImage):
    _default_proj = "EPSG:4326"

    def __new__(cls, op):
        assert isinstance(op, DaskMeta)
        self = super(IpeImage, cls).create(op)
        self._ipe_op = op
        if self.ipe.metadata["georef"] is None:
            self.__geo_transform__ = RatPolyTransform.from_rpcs(self.ipe.metadata["rpcs"])
        else:
            self.__geo_transform__ = AffineTransform.from_georef(self.ipe.metadata["georef"])
        self.__geo_interface__ = mapping(self._reproject(wkt.loads(self.ipe.metadata["image"]["imageBoundsWGS84"])))
        return self

    @property
    def __daskmeta__(self):
        return self.ipe

    @property
    def ipe(self):
        return self._ipe_op

    @property
    def ipe_id(self):
        return self.ipe._ipe_id

    @property
    def ntiles(self):
        size = float(self.ipe.metadata['image']['tileXSize'])
        return math.ceil((float(self.shape[-1]) / size)) * math.ceil(float(self.shape[1]) / size)

    @property
    def _rgb_bands(self):
        return [4,2,1]    

    @property
    def _ndvi_bands(self):
        return [7,4]

    def rgb(self, **kwargs):
        data = self[kwargs.get("bands", self._rgb_bands),...].read()
        data = np.rollaxis(data.astype(np.float32), 0, 3)
        lims = np.percentile(data, kwargs.get("stretch", [2,98]), axis=(0,1))
        for x in xrange(len(data[0,0,:])):
            top = lims[:,x][1]
            bottom = lims[:,x][0]
            data[:,:,x] = (data[:,:,x]-bottom)/float(top-bottom)
        return np.clip(data,0,1)

    def ndvi(self, **kwargs):
        data = self[self._ndvi_bands,...].read().astype(np.float32)
        return (data[0,:,:] - data[1,:,:]) / (data[0,:,:] + data[1,:,:])

    def plot(self, spec="rgb", **kwargs):
        if self.shape[0] == 1 or ("bands" in kwargs and len(kwargs["bands"]) == 1):
            super(IpeImage, self).plot(tfm=self._single_band, cmap="Greys_r", **kwargs)
        else:
            super(IpeImage, self).plot(tfm=getattr(self, spec), **kwargs)
    
    def _single_band(self, **kwargs):
        return self[0,:,:].read()

    def __getitem__(self, geometry):
        if isinstance(geometry, BaseGeometry) or getattr(geometry, "__geo_interface__", None) is not None:
            image = GeoImage.__getitem__(self, geometry)
            image._ipe_op = self._ipe_op
            return image
        else:
            image = super(IpeImage, self).__getitem__(geometry)
            image.__geo_interface__ = self.__geo_interface__
            image.__geo_transform__ = self.__geo_transform__
            image._ipe_op = self._ipe_op
            image.__class__ = self.__class__ 
            return image

    def read(self, bands=None):
        print('Fetching Image... {} {}'.format(self.ntiles, 'tiles' if self.ntiles > 1 else 'tile'))
        return super(IpeImage, self).read(bands=bands)
