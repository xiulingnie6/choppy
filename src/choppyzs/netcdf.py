#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compute zonal statistics of a netcdf."""
import os
import logging
from tempfile import TemporaryDirectory
import pandas as pd
import xarray as xr
import rioxarray
import re
import sys
import patoolib as pa
import rasterio as rio
import geopandas as gpd
from datetime import datetime
from rasterstats import zonal_stats
try:
    from choppyzs.imagediff import check_if_file_exists
    from choppyzs.logz import create_logger
except ImportError:
    from .imagediff import check_if_file_exists
    from .logz import create_logger

logger = create_logger()


class NetCDF2Stats():
    """Convert a netcdf timeseries to zonal_stats."""

    def __init__(self, shape_archive, nc_file, output_dir=os.getcwd(),
                 statistics='min,max,mean,median,majority,sum,std,count,range',
                 output_file='zonal_stats', all_touched=False,
                 output_format='csv', geometry=False):
        """Initialize the NetCDF2Stats class."""
        if output_format not in ['xlsx', 'csv', 'tsv', 'none', None]:
            raise RuntimeError(f'Format {output_format} is not acceptable!')
        self.output_format = output_format
        self.working_directory = TemporaryDirectory()
        if ',' in statistics:
            self.statistics = statistics.split(',')
        else:
            self.statistics = statistics
        self.all_touched = all_touched
        self.shape_archive = shape_archive
        self.nc_file = nc_file
        self.output_file = output_file + '.' + output_format
        self.geometry = geometry
        pa.extract_archive(shape_archive, outdir=self.working_directory.name)
        for file_name in os.listdir(self.working_directory.name):
            if file_name.endswith('.shp'):
                self.shape_file = os.path.join(self.working_directory.name,
                                               file_name)
        check_if_file_exists(self.shape_file)
        check_if_file_exists(self.nc_file)
        self.output_path = os.path.join(output_dir, self.output_file)
        if output_format == 'json':
            self.geojson = True
        else:
            self.geojson = False
        self.shape_df = gpd.read_file(self.shape_file)
        self.nc_ds = xr.open_dataset(self.nc_file, engine="rasterio")
        self.nc_ds = self.nc_ds.rio.write_crs("epsg:4326", inplace=True)
        #self.affine = rio.open(self.nc_file).transform
        self.df_list = []

    def chop(self, time_var='time', start_year=None, time_range=None, value_var='scpdsi'):
        """Chop the raster stats over the years."""
        nc_var = self.nc_ds[value_var]
        logger.info(f'nc_var length: {value_var}:{len(nc_var)}')
        org_nc_times = self.nc_ds[time_var].values
        if start_year:
            nc_times = [d for d in org_nc_times if datetime.fromisoformat(re.sub('T.*$', '', str(d))) >=  datetime.fromisoformat(f'{start_year}-01-01')]        
        elif time_range: # e.go. 11-12
            start_index, end_index = time_range.split('-')
            nc_times = org_nc_times[int(start_index):int(end_index)] # select noon
        else:
            nc_times = org_nc_times
        logger.info(f'Parsing {nc_times} out of {len(org_nc_times)} times')
        
        for nc_time in nc_times:
            logger.info(f'Parsing time {nc_time}')
            nc_arr = nc_var.sel(time=nc_time)
            logger.info(f'nc_arr length:{len(nc_arr)}')

            nc_arr_values = nc_arr.squeeze().values

            stats_data = zonal_stats(self.shape_file,
                                     nc_arr_values, affine=nc_arr.rio.transform(),
                                     stats=self.statistics,
                                     nodata=-999,
                                     geojson_out=self.geojson,
                                     all_touched=self.all_touched)
            sd = pd.DataFrame.from_dict(stats_data)
            df = pd.DataFrame(self.shape_df)
            dat = pd.concat([df, sd], axis=1)
            logging.info(f'{nc_time}')
            dat['time'] = nc_time
            if self.geometry is False:
                dat.drop(columns='geometry', inplace=True, errors='ignore')
            self.df_list.append(dat)

    def export(self):
        """Export the dataframe as the appropriate output."""
        self.df = pd.concat(self.df_list, ignore_index=True)
        if self.output_format == 'csv':
            self.df.to_csv(self.output_path, index=False)
        elif self.output_format == 'tsv':
            self.df.to_csv(self.output_path, sep='\t', index=False)
        elif self.output_format == 'xlsx':
            self.df.to_excel(self.output_path)
        elif self.output_format == 'none':
            logger.info(self.df)
        return self.df
