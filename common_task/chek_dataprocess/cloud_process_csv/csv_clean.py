from datetime import datetime
import pandas as pd
import asyncio
from multiprocessing import Pool
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from functools import partial


class DataProcessor:
    def __init__(self):
        self.csv_file = None
        self.df = None
        self.executor = ProcessPoolExecutor(max_workers=10)
        self.manager = Manager()
        self.shared_data = self.manager.dict()

    def async_process(self, csv_file: str = None):
        if csv_file:
            print(f'Post process {csv_file}')
            self.csv_file = csv_file
            self.df = pd.read_csv(csv_file)
        if self.df.empty:
            print('No data in this csv file!')
            return None
        # self.process_time()

        self.shared_data['df'] = self.df.to_dict()

        tasks = [
            self.executor.submit(partial(self.process_gps_data, self.shared_data)),
            self.executor.submit(partial(self.process_speed, self.shared_data)),
            self.executor.submit(partial(self.process_acc, self.shared_data))
        ]
        for task in tasks:
            task.result()

        self.executor.submit(partial(self.process_state, self.shared_data)).result()

        self.df = pd.DataFrame.from_dict(self.shared_data['df'])

        return self.df 


    def process(self, csv_file: str = None):
        if csv_file:
            print(f'Post process {csv_file}')
            self.csv_file = csv_file
            self.df = pd.read_csv(csv_file)
        if self.df.empty:
            print('No data in this csv file!')
            return None
        # self.process_time()
        self.process_gps_data()
        self.process_speed()
        self.process_acc()
        self.process_state()
        # self.process_weather()
        # self.process_road_scene()
        # self.process_light()
        # self.process_truck()
        return self.df

    def process_time(self):
        # drop invalid time
        start_t = None
        df_time = self.df['time'].copy()
        drop_idx = []
        for i, t in enumerate(self.df['time']):
            t = datetime.fromisoformat(t).tstamp() if isinstance(t, str) else t
            if t is None or t < 1e5:
                drop_idx.append(i)
                continue
            start_t = t if start_t is None else start_t
            df_time[i] -= start_t if start_t is not None else 0
        self.df.drop(index=drop_idx, inplace=True)
        df_time.drop(index=drop_idx, inplace=True)
        self.df['time'] = df_time
        self.df.reset_index(drop=True, inplace=True)

    def process_gps_data(self):
        df_gps_timestamp = self.df['gps_timestamp'].copy()
        df_gps_speed = self.df['gps_speed'].copy()
        df_lon = self.df['lon'].copy()
        df_lat = self.df['lat'].copy()
        for i, (t, gps_v, lon, lat) in enumerate(zip(self.df['gps_timestamp'], self.df['gps_speed'], self.df['lon'], self.df['lat'])):
            future_i, delta_t = self.get_idx_after_seconds(i, 1.5)
            futrure_gps_t = df_gps_timestamp[future_i]
            if pd.isna(t) or pd.isna(gps_v) or lon < 1 or lat < 1 or (delta_t > 1.5 and futrure_gps_t == t):
                df_gps_timestamp[i] = None
                df_gps_speed[i] = None
                df_lon[i] = None
                df_lat[i] = None
                continue
            # 将时间戳转换为datetime对象
            # t += 8*3600
            # dt_object = datetime.fromtimestamp(t)
            # 将datetime对象格式化为人类可读时间格式
            # human_readable_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
            # df_gps_timestamp[i] = human_readable_time
        self.df['gps_timestamp'] = df_gps_timestamp
        self.df['gps_speed'] = df_gps_speed
        self.df['lon'] = df_lon
        self.df['lat'] = df_lat

    # def process_speed(self):
    #     df_speed = self.df['speed'].copy()
    #     self.df.insert(4, 'speed_old', df_speed)
    #     next_valid_idx = -1
    #     pre_valid_v, pre_valid_gps_v = None, None
    #     # gps speed has about 1s delay
    #     for i, v in enumerate(self.df['speed']):
    #         gps_v = self.df['gps_speed'][self.get_idx_after_seconds(i, 1)[0]]
    #         is_valid_gps = self.is_valid_gps(i)
    #         # When gps is valid
    #         if is_valid_gps:
    #             if not pd.isna(v) and abs(gps_v - v) < 10:
    #                 pre_valid_v = v
    #                 pre_valid_gps_v = gps_v
    #             elif pre_valid_gps_v is not None and is_valid_gps:
    #                 df_speed[i] = max(
    #                     0, pre_valid_v + (gps_v - pre_valid_gps_v))
    #             else:
    #                 df_speed[i] = gps_v
    #             continue
    #         # If current gps is not valid, find the next valid v
    #         if next_valid_idx is not None and i > next_valid_idx:
    #             next_valid_idx = self.get_next_valid_speed_idx(i)
    #         expected_v = None
    #         if next_valid_idx is None:
    #             expected_v = df_speed[max(0, i-1)]
    #         else:
    #             pre_v, pre_t = df_speed[max(
    #                 0, i-1)], self.df['time'][max(0, i-1)]
    #             next_v, next_t = df_speed[next_valid_idx], self.df['time'][next_valid_idx]
    #             if i == 0:
    #                 expected_v = next_v
    #             else:
    #                 p = (self.df['time'][i] - pre_t) / (next_t - pre_t)
    #                 expected_v = p*next_v + (1-p)*pre_v
    #         if not pd.isna(v) and abs(v - expected_v) < 10:
    #             continue
    #         df_speed[i] = expected_v
    #     self.df['speed'] = df_speed

    # NOTE: 8000行 总耗时566s -> 5.14
    def process_speed(self):
        import numpy as np
        
        # 预先复制数据
        df_speed = self.df['speed'].copy()
        df_time = self.df['time'].values
        df_gps_speed = self.df['gps_speed'].values
        
        # 创建数组存储结果
        speed_values = df_speed.values
        data_len = len(speed_values)
        
        # 预计算1秒后的索引
        future_indices = np.zeros(data_len, dtype=int)
        for i in range(data_len):
            current_t = df_time[i]
            future_idx = i
            while future_idx < data_len - 1 and df_time[future_idx] - current_t < 1:
                future_idx += 1
            future_indices[i] = future_idx
        
        # 主处理循环
        pre_valid_v = None
        pre_valid_gps_v = None
        
        for i in range(data_len):
            gps_v = df_gps_speed[future_indices[i]]
            v = speed_values[i]
            
            # 检查GPS是否有效
            if not pd.isna(gps_v):
                if not pd.isna(v) and abs(gps_v - v) < 10:
                    pre_valid_v = v
                    pre_valid_gps_v = gps_v
                elif pre_valid_gps_v is not None:
                    speed_values[i] = max(0, pre_valid_v + (gps_v - pre_valid_gps_v))
                else:
                    speed_values[i] = gps_v
                continue
                
            # GPS无效时的处理
            if i > 0:
                expected_v = speed_values[i-1]
                if not pd.isna(v) and abs(v - expected_v) < 10:
                    continue
                speed_values[i] = expected_v
        
        # 更新DataFrame
        self.df.insert(4, 'speed_old', df_speed)
        self.df['speed'] = pd.Series(speed_values)

    def process_acc(self):
        df_speed = self.df['speed']
        df_acc = df_speed.copy()
        last_acc = 0
        for i, v in enumerate(df_speed):
            future_1s_idx, delta_t = self.get_idx_after_seconds(i, 1)
            nv = df_speed[future_1s_idx]
            acc = (nv-v)/3.6/delta_t if delta_t > 0 else last_acc
            last_acc = acc
            df_acc[i] = acc
            # df_acc[i] = a if abs(a) < 8 else 0
        self.df.insert(6, 'acc', df_acc)

    def process_state(self):
        df_state = self.df['auto_car'].copy()
        for i, (auto_icon, auto_car) in enumerate(zip(self.df['auto_icon'], self.df['auto_car'])):
            if auto_icon == auto_car or (pd.isna(auto_icon) and pd.isna(auto_car)) or i+1 == len(df_state):
                df_state[i] = auto_icon
                continue
            if not pd.isna(auto_icon) and pd.isna(auto_car):
                df_state[i] = auto_icon
                continue
            if pd.isna(auto_icon) and not pd.isna(auto_car):
                df_state[i] = auto_car
                continue
            # consider None
            future_7s_idx, delta_t = self.get_idx_after_seconds(i, 7)
            auto_icon_counts = self.df['auto_icon'][i +
                                                    1: future_7s_idx].value_counts(dropna=False)
            auto_car_counts = self.df['auto_car'][i +
                                                  1: future_7s_idx].value_counts(dropna=False)
            auto_icon_mode = None if len(
                auto_icon_counts.index) == 0 else auto_icon_counts.index[0]
            auto_car_mode = None if len(
                auto_car_counts.index) == 0 else auto_car_counts.index[0]
            if pd.isna(auto_icon_mode) and pd.isna(auto_car_mode):
                df_state[i] = auto_icon
            if auto_icon_mode == auto_car_mode:
                df_state[i] = auto_icon_mode
            elif not pd.isna(auto_icon_mode) and pd.isna(auto_car_mode):
                df_state[i] = auto_icon_mode
            elif pd.isna(auto_icon_mode) and not pd.isna(auto_car_mode):
                df_state[i] = auto_car_mode
            else:
                df_state[i] = auto_icon_mode if auto_icon_counts.iloc[0] >= auto_car_counts.iloc[0] else auto_car_mode
        self.df.insert(4, 'state_no_smooth', df_state)
        # smooth state
        in_state, in_state_seconds, in_state_start_idx = None, 0, 0
        for i, state in enumerate(df_state):
            if i+1 >= len(self.df):
                break
            if pd.isna(state):
                state = None
            if state != in_state:
                # state change
                expected_state = in_state
                pre_valid_idx = in_state_start_idx - 1
                if in_state_seconds < 3:
                    future_3s_idx, _ = self.get_idx_after_seconds(i, 3)
                    future_state_counts = df_state[i:
                                                   future_3s_idx].value_counts(dropna=False)
                    expected_state = future_state_counts.index[0]
                    if pre_valid_idx >= 0:
                        pre_valid_state = df_state[pre_valid_idx]
                        if (in_state == 'lcc' or in_state == 'noa') and (pre_valid_state == 'lcc' or pre_valid_state == 'noa'):
                            expected_state = in_state
                        elif not pd.isna(pre_valid_state) and pre_valid_state == state:
                            expected_state = pre_valid_state
                        elif pre_valid_state == in_state or future_state_counts.iloc[0] < (future_3s_idx-i)/2:
                            expected_state = pre_valid_state
                # short None between noa or lcc
                if pd.isna(in_state) and in_state_seconds < 10:
                    if pre_valid_idx >= 0:
                        pre_valid_state = df_state[pre_valid_idx]
                        if (pre_valid_state == 'lcc' or pre_valid_state == 'noa') and (state == 'lcc' or state == 'noa'):
                            expected_state = pre_valid_state
                if expected_state != in_state:
                    pre_idx = i-1
                    while pre_idx >= 0 and pre_idx > pre_valid_idx:
                        df_state[pre_idx] = expected_state
                        pre_idx -= 1
                in_state = state
                in_state_seconds = 0
                in_state_start_idx = i
            else:
                in_state_seconds = self.df['time'][i] - \
                    self.df['time'][in_state_start_idx]
        self.df.insert(5, 'state', df_state)

    def process_weather(self):
        self.df['weather'] = self.smooth(
            self.df['weather'], look_backward=100, look_ahead=100)

    def process_road_scene(self):
        self.df['road_scene'] = self.smooth(
            self.df['road_scene'], look_backward=30, look_ahead=30)

    def process_light(self):
        self.df['light'] = self.smooth(
            self.df['light'], look_backward=100, look_ahead=100)

    def process_truck(self):
        df_truck_min_dis = self.df['truck_min_dis'].copy()
        df_truck_lon_dis = self.df['truck_lon_dis'].copy()
        df_truck_lat_dis = self.df['truck_lat_dis'].copy()
        pre_dis, pre_lon_dis, pre_lat_dis = 999, 999, 999
        for i, (dis, lon_dis, lat_dis) in enumerate(zip(self.df['truck_min_dis'], self.df['truck_lon_dis'], self.df['truck_lat_dis'])):
            dis_mean_future = df_truck_min_dis[i +
                                               1:min(len(df_truck_min_dis)-1, i+10)].mean()
            if dis > 100 and pre_dis < dis and dis_mean_future < 999:
                df_truck_min_dis[i], df_truck_lon_dis[i], df_truck_lat_dis[i] = pre_dis, pre_lon_dis, pre_lat_dis
            pre_dis, pre_lon_dis, pre_lat_dis = dis, lon_dis, lat_dis
        self.df['truck_min_dis'] = df_truck_min_dis
        self.df['truck_lon_dis'] = df_truck_lon_dis
        self.df['truck_lat_dis'] = df_truck_lat_dis

    def is_valid_speed(self, current_idx):
        v = self.df['speed'][current_idx]
        past_3s_i, delta_t = self.get_idx_before_seconds(current_idx, 3)
        future_3s_i, delta_t = self.get_idx_after_seconds(current_idx, 3)
        v_median = self.df['speed'][past_3s_i: future_3s_i].median()
        v_mean = self.df['speed'][past_3s_i: future_3s_i].mean()
        if not pd.isna(v) and abs(v_mean - v) < 10 and abs(v_median - v) < 10:
            return True
        return False

    def get_next_valid_speed_idx(self, current_idx):
        future_i = current_idx + 1
        # try through valid gps
        future_10s_i, delta_t = self.get_idx_after_seconds(current_idx, 10)
        while future_i < len(self.df) and future_i <= future_10s_i:
            # future 10s
            v = self.df['speed'][future_i]
            gps_v = self.df['gps_speed'][self.get_idx_after_seconds(
                future_i, 1)[0]]
            if self.is_valid_gps(future_i) and not pd.isna(v) and abs(gps_v - v) < 10:
                return future_i
            future_i += 1
        # try other
        future_i = current_idx + 1
        while future_i < len(self.df):
            if self.is_valid_speed(future_i):
                return future_i
            future_i += 1
        return None

    def smooth(self, df_data, look_backward=10, look_ahead=10):
        # smooth with values in future
        df_copy = df_data.copy()
        pre_v = None
        for i, v in enumerate(df_data):
            v_mode_future = df_data[i +
                                    1:min(len(df_data)-1, i+look_ahead)].mode().tolist()
            if v == pre_v or v in v_mode_future:
                continue
            else:
                df_copy[i] = v_mode_future[0] if len(
                    v_mode_future) > 0 else pre_v
                v = df_copy[i]
            pre_v = v
        # smooth with values in previous
        pre_v = None
        reversed_df_copy = pd.Series(reversed(df_copy))
        for i, v in enumerate(reversed_df_copy):
            v_mode_future = reversed_df_copy[i +
                                             1:min(len(reversed_df_copy)-1, i+look_backward)].mode().tolist()
            if v == pre_v or v in v_mode_future:
                continue
            else:
                reversed_df_copy[i] = v_mode_future[0] if len(
                    v_mode_future) > 0 else pre_v
                v = reversed_df_copy[i]
            pre_v = v
        df_copy = pd.Series(reversed_df_copy)
        return df_copy

    def get_idx_after_seconds(self, current_idx, seconds):
        current_t = self.df['time'][current_idx]
        delta_t = 0
        future_idx = current_idx
        while future_idx < len(self.df) and delta_t < seconds:
            delta_t = self.df['time'][future_idx] - current_t
            future_idx += 1
        return future_idx-1, delta_t

    def get_idx_before_seconds(self, current_idx, seconds):
        current_t = self.df['time'][current_idx]
        delta_t = 0
        past_idx = current_idx
        while past_idx > 0 and delta_t < seconds:
            delta_t = current_t - self.df['time'][past_idx]
            past_idx -= 1
        return past_idx+1, delta_t

    def get_idx_by_frame_id(self, frame_id):
        l_idx, r_idx = 0, len(self.df)-1
        while l_idx <= r_idx:
            m_idx = l_idx+int((r_idx-l_idx)/2)
            m_frame_id = self.df['frame'][m_idx]
            if m_frame_id < frame_id:
                l_idx = m_idx+1
            elif m_frame_id > frame_id:
                r_idx = m_idx-1
            else:
                return m_idx
        return r_idx

    def is_valid_gps(self, current_idx):
        past_idx, _ = self.get_idx_before_seconds(current_idx, 5)
        future_idx, _ = self.get_idx_after_seconds(current_idx, 5)
        recent_gps_speed_df = self.df['gps_speed'][past_idx:future_idx]
        for i in range(past_idx, future_idx-1):
            p_gps_speed = recent_gps_speed_df[i]
            n_gps_speed = recent_gps_speed_df[i+1]
            if pd.isna(p_gps_speed) or abs(p_gps_speed-n_gps_speed) > 40:
                return False
            future_3s_idx, delta_t = self.get_idx_after_seconds(i, 3)
            if delta_t >= 3 and self.df['gps_timestamp'][future_3s_idx] == self.df['gps_timestamp'][i]:
                return False
        return True

    def save(self, output_csv_file: str):
        print(f'Save to {output_csv_file}')
        self.df.to_csv(output_csv_file, index=False)

    def recover(self, pro_csv_file: str = None):
        if pro_csv_file:
            self.csv_file = pro_csv_file
            self.df = pd.read_csv(pro_csv_file)
        # self.df.drop(columns=['acc', 'state_no_smooth',
        #              'state', 'speed'], inplace=True)
        self.df.rename(columns={'speed_old': 'speed'}, inplace=True)
        timestamp_now = datetime.now().timestamp()
        df_time = self.df['time'].copy()
        df_gps_timestamp = self.df['gps_timestamp'].copy()
        # for i in range(len(self.df)):
        #     df_time[i] += timestamp_now
        #     if not pd.isna(df_gps_timestamp[i]):
        #         df_gps_timestamp[i] = datetime.strptime(
        #             df_gps_timestamp[i], '%Y-%m-%d %H:%M:%S').timestamp()

        df_gps_timestamp = df_gps_timestamp.apply(lambda x: datetime.fromtimestamp(x / 1000).strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else x)
        # 时间归一化
        df_time = df_time - df_time.iloc[0]

        self.df['time'] = df_time
        self.df['gps_timestamp'] = df_gps_timestamp


if __name__ == '__main__':
    data_processor = DataProcessor()
    data_processor.recover('../82bdb7187ae7_20231113_083430.csv')
    data_processor.process()
    data_processor.save('pro.csv')
