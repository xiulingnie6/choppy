#!/usr/bin/env python3
"""
    This bins time series drought data by boundaries described in the
    given shape file.
"""
from tempfile import TemporaryDirectory
from pathlib import Path

import patoolib
import xarray
import rasterio
import pandas as pd
import geopandas as gpd
import fiona
from tqdm import tqdm
from rasterstats import zonal_stats


try:
    from choppyzs.imagediff import check_if_file_exists
    from choppyzs.logz import create_logger
except ImportError:
    from .imagediff import check_if_file_exists
    from .logz import create_logger

logger = create_logger()


def ts_to_stats(shape_file_archive, ts_file):
    """ Aggregate time series drought data by month and region.

    :param shape_file_archive: zip file of boundaries
    :param ts_file: is NetCDF file of time series drought data
    :return: dataframe of drought data by region and month
    """
    def read_shapefile(shape_file_archive):
        """ Create a geopandas dataframe and a fiona db from shapefile

        :param shape_file_archive: containing boundaries
        :return: geopandas dataframe and fiona db of boundaries
        """
        # First unroll the shape file into a temporary directory,
        # and then extract the shapefile from it.
        with TemporaryDirectory() as temp_dir:
            patoolib.extract_archive(shape_file_archive, outdir=temp_dir)

            # TODO Wrap this in exception handling in case there are
            # no found shape files.
            shape_file = list(Path(temp_dir).glob('*.shp'))[0]

            logger.info(f'Reading {shape_file}')

            # We want this geopandas dataframe since we're going to be
            # using it over and over again to build the returned
            # dataframe.
            boundaries_df = gpd.read_file(shape_file)
            # We don't need the geometry here; we just want the salient
            # dataframe columns that will later be written.
            boundaries_df.drop(columns='geometry',
                               inplace=True,
                               errors='ignore')

            # We want to read the shape file separately into a local
            # spatial database to quickly do geoprocessing.  And we
            # do this once right here so we're not constantly re-reading
            # this information.
            boundaries_db = fiona.open(shape_file)

            return boundaries_df, boundaries_db

    def read_ts(ts_file):
        """ read the time series data file
        :returns: time series data and affine transform
        """
        logger.info(f'Reading {ts_file}')

        # Get the time series of drought data
        drought_ts = xarray.open_dataset(ts_file)

        # Bendy affine transform data
        affine = rasterio.open(ts_file).transform

        return drought_ts, affine

    def chop(boundaries_df, boundaries_db, drought_ts, affine):
        """ perform the data aggregation
        :return: dataframe of aggregated data
        """
        scpdsi = drought_ts['scpdsi']
        times = drought_ts['time'].values
        dfs = []

        for nc_time in tqdm(times):
            # logger.info(f'Parsing time {nc_time}')
            nc_arr = scpdsi.sel(time=nc_time)
            nc_arr_values = nc_arr.values

            # Note that we use the fiona database instead of the shape file,
            # which save a little bit of time.
            stats_data = zonal_stats(boundaries_db,
                                     nc_arr_values, affine=affine,
                                     stats='min,max,mean,median,majority,sum,std,count,range'.split(','),
                                     nodata=-9999, # to shut up stupid warning
                                     geojson_out=False,
                                     all_touched=True)
            sd = pd.DataFrame.from_dict(stats_data)

            # We also save a little time by just reusing the static dataframe
            # instead of running through a constructor over and over again.
            # df = pd.DataFrame(self.shape_df)
            dat = pd.concat([boundaries_df, sd], axis=1)

            dat['time'] = nc_time

            dfs.append(dat)

        return pd.concat(dfs, ignore_index=True)

    check_if_file_exists(shape_file_archive)
    check_if_file_exists(ts_file)

    # Extra a geopandas dataframe and a fiona database from the
    # given shape file.
    boundaries_df, boundaries_db = read_shapefile(shape_file_archive)

    # Now grab the time series data
    drought_ts, affine = read_ts(ts_file)

    # Now do the chopping
    df = chop(boundaries_df, boundaries_db, drought_ts, affine)

    return df


if __name__ == '__main__':
    logger.info('running ts2stats test')

    df = ts_to_stats('/examples/lichtenstein.zip',
                     '/examples/drought.nc')

    if df is not none and not df.empty:
        df.to_csv('new_zonal_stats.csv')
    else:
        logger.warning('No data to write.')

    logger.info('Done')
