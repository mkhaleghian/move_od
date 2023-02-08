
import pandas as pd
import geopandas as gpd
import numpy as np
from datetime  import datetime, timedelta
import random
import tqdm
from tqdm.notebook import tqdm_notebook

from shapely.geometry import Point

class Sg_combs:

    def __init__(self, county_cbg, data_path, ms_enabled) -> None:
        self.county_cbg = county_cbg
        self.data_path =data_path
        self.ms_enabled = ms_enabled 
        # self.safe_df = safe_df

    def intpt_func(row):
        return Point(row['INTPTLON'], row['INTPTLAT'])

    def func_home_pt(row):
        return Point(row.home_loc_lon, row.home_loc_lat)
        
    def func_work_pt(row):
        return Point(row.work_loc_lon, row.work_loc_lat)


    def generate_combs(self):
    #loading geometry data
        county_cbg = pd.read_csv(f'{self.data_path}/county_cbg.csv')
        county_cbg['intpt'] = county_cbg[['INTPTLAT', 'INTPTLON']].apply(lambda p: Sg_combs.intpt_func(p), axis=1)
        county_cbg = gpd.GeoDataFrame(county_cbg, geometry=gpd.GeoSeries.from_wkt(county_cbg.geometry))
        county_cbg.GEOID = county_cbg.GEOID.astype(str)


        #loading residential buildings
        res_build = pd.read_csv(f'{self.data_path}/county_residential_buildings.csv', index_col=0)
        res_build = gpd.GeoDataFrame(res_build, geometry=gpd.GeoSeries.from_wkt(res_build.geometry))
        res_build['location'] = res_build.geometry.apply(lambda p: [p.y, p.x])

        #loading work buildings
        com_build = pd.read_csv(f'{self.data_path}/county_work_loc_poi_com_civ.csv', index_col=0)
        com_build = gpd.GeoDataFrame(com_build, geometry=gpd.GeoSeries.from_wkt(com_build.geometry))
        com_build['location'] = com_build.geometry.apply(lambda p: [p.y, p.x])
        com_build = com_build.reset_index()
        com_build.GEOID = com_build.GEOID.astype(str)

        #loading all buildings (MS dataset)
        ms_build = pd.read_csv(f'{self.data_path}/county_buildings_MS.csv')
        ms_build = gpd.GeoDataFrame(ms_build, geometry=gpd.GeoSeries.from_wkt(ms_build.geo_centers))
        ms_build.GEOID = ms_build.GEOID.astype(str)
        ms_build['location'] = ms_build.geometry.apply(lambda p: [p.y, p.x])


        def datetime_range(start, end, delta):
            current = start
            while current < end:
                yield current
                current += delta


        #generating array of start and return times (in 15 min intervals)
        times_morning = [datetime.strptime(dt.strftime('%H:%M'), '%H:%M') for dt in 
            datetime_range(datetime(2016, 9, 1, 7), datetime(2016, 9, 1, 9, 10), 
            timedelta(minutes=15))]
        times_evening = [datetime.strptime(dt.strftime('%H:%M'), '%H:%M') for dt in 
            datetime_range(datetime(2016, 9, 1, 16), datetime(2016, 9, 1, 18, 10), 
            timedelta(minutes=15))]


        res_build.GEOID = res_build.GEOID.astype(str)
        com_build.GEOID = com_build.GEOID.astype(str)


        #input safegraph preprocessed data
        sg = gpd.read_file(f'{self.data_path}/county_sg_jan_mar_reduced_cols.csv')


        #grouping home and work location movements to get total no of movements
        sg = sg.groupby(['home_cbg', 'poi_cbg']).agg(frequency=('frequency', sum), visits_monday=('visits_monday', sum), visits_tuesday=('visits_tuesday', sum), visits_wednesday=('visits_wednesday', sum), visits_thursday=('visits_thursday', sum), visits_friday=('visits_friday', sum), visits_saturday=('visits_saturday', sum), visits_sunday=('visits_sunday', sum) ).reset_index()


        #setting the random seed
        np.random.seed(42)
        random.seed(42)


        prob_matrix_sg = gpd.GeoDataFrame()
        for idx, movement in tqdm_notebook(sg.iterrows(), total=sg.shape[0]):


            res = res_build[res_build.GEOID == movement.h_geocode].reset_index(drop=True)
            if res.empty:
                try:
                    res = ms_build[ms_build.GEOID == movement.h_geocode].sample(n=movement.total_jobs, random_state=42).reset_index(drop=True)
                except:
                    if self.ms_enabled:
                        try:
                            res = ms_build[ms_build.GEOID == movement.h_geocode].sample(n=movement.total_jobs, random_state=42, replace=True).reset_index(drop=True)
                        except:
                            res = county_cbg[county_cbg.GEOID == movement.h_geocode]

            com = com_build[com_build.GEOID == movement.w_geocode].reset_index(drop=True)
            if com.empty:
                try:
                    com = ms_build[ms_build.GEOID == movement.w_geocode].sample(n=movement.total_jobs, random_state=42).reset_index(drop=True)
                except:
                    if self.ms_enabled:
                        try:
                            com = ms_build[ms_build.GEOID == movement.w_geocode].sample(n=movement.total_jobs, random_state=42, replace=True).reset_index(drop=True)
                        except:
                            com = county_cbg[county_cbg.GEOID == movement.w_geocode]
            r = res
            c = com

            for freq in range(int(movement.frequency/12)):

                if c.empty:
                    c = com
                if r.empty:
                    r = res
                
                rand_r = random.randrange(r.shape[0])
                rand_c = random.randrange(c.shape[0])
                r_df = r.iloc[rand_r]
                c_df = c.iloc[rand_c]
                r = r.drop([rand_r]).reset_index(drop=True)
                c = c.drop([rand_c]).reset_index(drop=True)

                time_slot1 = np.random.choice(times_morning, size=1, replace=True)
                time_slot2 = np.random.choice(times_evening, size=1, replace=True)

                temp = gpd.GeoDataFrame()

                temp.loc[freq, 'home_cbg'] = movement.home_cbg
                temp.loc[freq, 'poi_cbg'] = movement.poi_cbg
                temp.loc[freq, 'frequency'] = movement.frequency
                temp.loc[freq, 'home_loc_lat'] = r_df.location[0]
                temp.loc[freq, 'home_loc_lon'] = r_df.location[1]
                temp.loc[freq, 'work_loc_lat'] = c_df.location[0]
                temp.loc[freq, 'work_loc_lon'] = c_df.location[1]
                temp.loc[freq, 'go_time'] = time_slot1[0]
                temp.loc[freq, 'go_time_secs'] = (time_slot1[0] - datetime(1900, 1, 1)).total_seconds()
                temp.loc[freq, 'go_time_str'] = time_slot1[0].strftime('%H:%M')
                temp.loc[freq, 'return_time'] = time_slot2[0]
                temp.loc[freq, 'return_time_secs'] = (time_slot2[0] - datetime(1900, 1, 1)).total_seconds()
                temp.loc[freq, 'return_time_str'] = time_slot2[0].strftime('%H:%M')

                # temp.loc[job, 'home_geom'] = Point([r_df.location[1], r_df.location[0]])
                prob_matrix_sg = prob_matrix_sg.append(temp, ignore_index=True)

        prob_matrix_sg['home_geom'] = prob_matrix_sg[['home_loc_lat', 'home_loc_lon']].apply(lambda row: Sg_combs.func_home_pt(row), axis=1)
        prob_matrix_sg['work_geom'] = prob_matrix_sg[['work_loc_lat', 'work_loc_lon']].apply(lambda row: Sg_combs.func_work_pt(row), axis=1)

    # convert the lat and lon points to shapely Points

        prob_matrix_sg.to_csv(f'{self.data_path}/county_sg_combinations.csv', index=False)

# prob_matrix_sg.shape


# prob_matrix_sg.drop(['home_geom', 'work_geom'], axis=1).to_parquet('sg_combinations_new.parquet', index=False)


