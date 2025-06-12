# # # import com.vehicle.saas.proto.SaasMessageHandle as proto  # 假设已经生成了对应的Python代码

# # class ChekMessageParser:
# #     def __init__(self, chek_message):
# #         self.chek_message = chek_message

# #     def parse(self):
# #         print( self.chek_message.journey.auto.intervention )
        
# #         data = {
# #             "name": self.chek_message.user.name if self.chek_message.user else "",
# #             "id": self.chek_message.user.id if self.chek_message.user else 0,
# #             "brand": self.chek_message.car.brand if self.chek_message.car else "",
# #             "model": self.chek_message.car.model if self.chek_message.car else "",
# #             "software_config": self.chek_message.car.version if self.chek_message.car else "",
# #             "journey_category": "", 

# #             # "polar_star": {
# #             #     "urban": {
# #             #         "turn_cnt": self.chek_message.journey.polarStarUrban.turn_cnt if self.chek_message.journey.polarStarUrban else 0,
# #             #         "turn_pass_cnt": self.chek_message.journey.polarStarUrban.turn_pass_cnt if self.chek_message.journey.polarStarUrban else 0,
# #             #         "turn_pass_rate": self.chek_message.journey.polarStarUrban.turn_pass_rate if self.chek_message.journey.polarStarUrban else 0,
# #             #         "urban_road_coverage": self.chek_message.journey.polarStarUrban.urban_road_coverage if self.chek_message.journey.polarStarUrban else 0,
# #             #         "auto_driving_efficiency": self.chek_message.journey.polarStarUrban.auto_driving_efficiency if self.chek_message.journey.polarStarUrban else 0
# #             #     },
# #             #     "highway": {
# #             #         "lane_change_cnt": self.chek_message.journey.polarStarhighway.lane_change_cnt if self.chek_message.journey.polarStarhighway else 0,
# #             #         "lane_change_successful_cnt": self.chek_message.journey.polarStarhighway.lane_change_successful_cnt if self.chek_message.journey.polarStarhighway else 0,
# #             #         "up_down_ramps_cnt": self.chek_message.journey.polarStarhighway.up_down_ramps_cnt if self.chek_message.journey.polarStarhighway else 0,
# #             #         "up_down_ramps_successful_cnt": self.chek_message.journey.polarStarhighway.up_down_ramps_successful_cnt if self.chek_message.journey.polarStarhighway else 0,
# #             #         "construction_scene_cnt": self.chek_message.journey.polarStarhighway.construction_scene_cnt if self.chek_message.journey.polarStarhighway else 0,
# #             #         "construction_scene_successful_cnt": self.chek_message.journey.polarStarhighway.construction_scene_successful_cnt if self.chek_message.journey.polarStarhighway else 0,
# #             #         "lane_change_rate": self.chek_message.journey.polarStarhighway.lane_change_rate if self.chek_message.journey.polarStarhighway else 0,
# #             #         "up_down_ramps_successful_rate": self.chek_message.journey.polarStarhighway.up_down_ramps_successful_rate if self.chek_message.journey.polarStarhighway else 0,
# #             #         "construction_scene_successful_rate": self.chek_message.journey.polarStarhighway.construction_scene_successful_rate if self.chek_message.journey.polarStarhighway else 0
# #             #     }
# #             # },
# #             "auto_mileages": self.chek_message.journey.odometer_auto if self.chek_message.journey else 0,
# #             "total_mileages": self.chek_message.journey.odometer_total if self.chek_message.journey else 0,
# #             "frames": self.chek_message.journey.auto.frames if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_frames": self.chek_message.journey.auto.frames if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "noa_frames": self.chek_message.journey.noa.frames if self.chek_message.journey and self.chek_message.journey.noa else 0,
# #             "lcc_frames": self.chek_message.journey.lcc.frames if self.chek_message.journey and self.chek_message.journey.lcc else 0,
# #             "driver_frames": self.chek_message.journey.driver.frames if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "auto_speed_average": self.chek_message.journey.auto.speed_average if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_max_speed": self.chek_message.journey.auto.speed_max if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "invervention_risk_proportion": self.chek_message.journey.auto.intervention_risk /self.chek_message.journey.auto.intervention if self.chek_message.journey and self.chek_message.journey.auto.intervention and self.chek_message.journey.auto.intervention_risk else 0,
# #             "invervention_mpi": self.chek_message.journey.auto.mpi if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.mpi else 0,
# #             "invervention_risk_mpi": self.chek_message.journey.auto.mpi_risk if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.mpi_risk else 0,
# #             "invervention_cnt": self.chek_message.journey.auto.intervention if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.intervention else 0,
# #             "invervention_risk_cnt": self.chek_message.journey.auto.intervention_risk if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.intervention_risk else 0,
# #             "noa_auto_mileages": self.chek_message.journey.noa.odometer if self.chek_message.journey and self.chek_message.journey.noa else 0,
# #             "noa_auto_mileages_proportion": self.chek_message.journey.noa.odometer/(self.chek_message.journey.noa.odometer+self.chek_message.journey.lcc.odometer) if  self.chek_message.journey.noa and self.chek_message.journey.lcc else 0, 
# #             "noa_invervention_risk_proportion": self.chek_message.journey.noa.intervention_risk / self.chek_message.journey.noa.intervention if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.intervention and self.chek_message.journey.noa.intervention_risk else 0,
# #             "noa_invervention_mpi": self.chek_message.journey.noa.mpi if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.mpi else 0,
# #             "noa_invervention_risk_mpi": self.chek_message.journey.noa.mpi_risk if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.mpi_risk else 0,
# #             "noa_invervention_cnt": self.chek_message.journey.noa.intervention if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.intervention else 0,
# #             "noa_invervention_risk_cnt": self.chek_message.journey.noa.intervention_risk if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.intervention_risk else 0,
# #             "lcc_invervention_risk_proportion": self.chek_message.journey.lcc.intervention_risk / self.chek_message.journey.lcc.intervention if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.intervention and self.chek_message.journey.lcc.intervention_risk else 0,
# #             "lcc_invervention_mpi": self.chek_message.journey.lcc.mpi if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.mpi else 0,
# #             "lcc_invervention_risk_mpi": self.chek_message.journey.lcc.mpi_risk if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.mpi_risk else 0,
# #             "lcc_invervention_cnt": self.chek_message.journey.lcc.intervention if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.intervention else 0,
# #             "lcc_invervention_risk_cnt": self.chek_message.journey.lcc.intervention_risk if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.intervention_risk else 0,
# #             "lcc_auto_mileages": self.chek_message.journey.lcc.odometer if self.chek_message.journey and self.chek_message.journey.lcc else 0,
# #             "lcc_auto_mileages_proportion": self.chek_message.journey.lcc.odometer/(self.chek_message.journey.noa.odometer+self.chek_message.journey.lcc.odometer) if  self.chek_message.journey.noa and self.chek_message.journey.lcc else 0,  
# #             "auto_dcc_max": self.chek_message.journey.auto.dcc_max if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_dcc_frequency": self.chek_message.journey.auto.dcc_frequency if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_dcc_cnt": self.chek_message.journey.auto.dcc_cnt if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_dcc_duration": self.chek_message.journey.auto.dcc_duration if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_dcc_average_duration": self.chek_message.journey.auto.dcc_duration/self.chek_message.journey.auto.dcc_cnt if self.chek_message.journey.auto and self.chek_message.journey.auto.dcc_cnt else 0 ,  
# #             "auto_dcc_average": self.chek_message.journey.auto.dcc_average if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_acc_max": self.chek_message.journey.auto.acc_max if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_acc_frequency": self.chek_message.journey.auto.acc_frequency if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_acc_cnt": self.chek_message.journey.auto.acc_cnt if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_acc_duration": self.chek_message.journey.auto.acc_duration if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "auto_acc_average_duration": self.chek_message.journey.auto.acc_duration/self.chek_message.journey.auto.acc_cnt if self.chek_message.journey.auto.acc_duration and self.chek_message.journey.auto.acc_cnt else 0,  # 未在原始数据中找到直接对应字段，设为0
# #             "auto_acc_average": self.chek_message.journey.auto.acc_average if self.chek_message.journey and self.chek_message.journey.auto else 0,
# #             "driver_mileages": self.chek_message.journey.driver.odometer if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_dcc_max": self.chek_message.journey.driver.dcc_max if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_dcc_frequency": self.chek_message.journey.driver.dcc_frequency if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_acc_max": self.chek_message.journey.driver.acc_max if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_acc_frequency": self.chek_message.journey.driver.acc_frequency if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_speed_average": self.chek_message.journey.driver.speed_average if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_speed_max": self.chek_message.journey.driver.speed_max if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_dcc_cnt": self.chek_message.journey.driver.dcc_cnt if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "driver_acc_cnt": self.chek_message.journey.driver.acc_cnt if self.chek_message.journey and self.chek_message.journey.driver else 0,
# #             "journey_start_time": "",  # 未在原始数据中找到对应字段，设为空
# #             "journey_end_time": "",  # 未在原始数据中找到对应字段，设为空
# #             "journey_generated_time": "",  # 未在原始数据中找到对应字段，设为空
# #             "journey_status": "",  # 未在原始数据中找到对应字段，设为空
# #             "auto_MBTI": self.chek_message.car.MBTI if self.chek_message.car else "",
# #             "standby_MBTI": "",  # 未在原始数据中找到对应字段，设为空
# #         }

# #         return data
    
# # # import com.vehicle.saas.proto.SaasMessageHandle as proto  # 假设已经生成了对应的Python代码

# # class ChekMessageParser:
# #     def __init__(self, chek_message):
# #         self.chek_message = chek_message

# #     def parse(self):
# #         data = {
# #             "name": self.chek_message.user.name if self.chek_message.user else "",
# #             "id": self.chek_message.user.id if self.chek_message.user else 0,
# #             "brand": self.chek_message.car.brand if self.chek_message.car else "",
# #             "model": self.chek_message.car.model if self.chek_message.car else "",
# #             "software_config": self.chek_message.car.software_version if self.chek_message.car else "",
# #             "journey_category": "", 
# #             "city_status_code": self.chek_message.journeyStatistics.cityNoaInterventionReseason.city_noa_merge_code if self.chek_message.journeyStatistics else 0,
# #             "city": self.chek_message.description.city if self.chek_message.description else "",
     
# #             "polar_star": {
# #                 "urban": {
# #                     "turn_cnt": self.chek_message.journeyStatistics.polarStarUrban.turn_cnt if self.chek_message.journeyStatistics.polarStarUrban else 0,
# #                     "turn_pass_cnt": self.chek_message.journeyStatistics.polarStarUrban.turn_pass_cnt if self.chek_message.journeyStatistics.polarStarUrban else 0,
# #                     "turn_pass_rate": self.chek_message.journeyStatistics.polarStarUrban.turn_pass_rate if self.chek_message.journeyStatistics.polarStarUrban else 0,
# #                     "urban_road_coverage": self.chek_message.journeyStatistics.polarStarUrban.urban_road_coverage if self.chek_message.journeyStatistics.polarStarUrban else 0,
# #                     "auto_driving_efficiency": self.chek_message.journeyStatistics.polarStarUrban.auto_driving_efficiency if self.chek_message.journeyStatistics.polarStarUrban else 0
# #                 },
# #                 "highway": {
# #                     "lane_change_cnt": self.chek_message.journeyStatistics.polarStarhighway.lane_change_cnt if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "lane_change_successful_cnt": self.chek_message.journeyStatistics.polarStarhighway.lane_change_successful_cnt if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "up_down_ramps_cnt": self.chek_message.journeyStatistics.polarStarhighway.up_down_ramps_cnt if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "up_down_ramps_successful_cnt": self.chek_message.journeyStatistics.polarStarhighway.up_down_ramps_successful_cnt if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "construction_scene_cnt": self.chek_message.journeyStatistics.polarStarhighway.construction_scene_cnt if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "construction_scene_successful_cnt": self.chek_message.journeyStatistics.polarStarhighway.construction_scene_successful_cnt if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "lane_change_rate": self.chek_message.journeyStatistics.polarStarhighway.lane_change_rate if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "up_down_ramps_successful_rate": self.chek_message.journeyStatistics.polarStarhighway.up_down_ramps_successful_rate if self.chek_message.journeyStatistics.polarStarhighway else 0,
# #                     "construction_scene_successful_rate": self.chek_message.journeyStatistics.polarStarhighway.construction_scene_successful_rate if self.chek_message.journeyStatistics.polarStarhighway else 0
# #                 }
# #             },
# #             "auto_mileages": self.chek_message.journeyStatistics.odometer_auto if self.chek_message.journeyStatistics else 0,
# #             "total_mileages": self.chek_message.journeyStatistics.odometer_total if self.chek_message.journeyStatistics else 0,
# #             "frames": self.chek_message.journeyStatistics.auto.frames if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_frames": self.chek_message.journeyStatistics.auto.frames if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "noa_frames": self.chek_message.journeyStatistics.noa.frames if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.noa else 0,
# #             "lcc_frames": self.chek_message.journeyStatistics.lcc.frames if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.lcc else 0,
# #             "driver_frames": self.chek_message.journeyStatistics.driver.frames if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "auto_speed_average": self.chek_message.journeyStatistics.auto.speed_average if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_max_speed": self.chek_message.journeyStatistics.auto.speed_max if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "invervention_risk_proportion": self.chek_message.journeyStatistics.auto.intervention_statistics.risk_proportion if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto and self.chek_message.journeyStatistics.auto.intervention_statistics else 0,
# #             "invervention_mpi": self.chek_message.journeyStatistics.auto.intervention_statistics.mpi if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto and self.chek_message.journeyStatistics.auto.intervention_statistics else 0,
# #             "invervention_risk_mpi": self.chek_message.journeyStatistics.auto.intervention_statistics.risk_mpi if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto and self.chek_message.journeyStatistics.auto.intervention_statistics else 0,
# #             "invervention_cnt": self.chek_message.journeyStatistics.auto.intervention_statistics.cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto and self.chek_message.journeyStatistics.auto.intervention_statistics else 0,
# #             "invervention_risk_cnt": self.chek_message.journeyStatistics.auto.intervention_statistics.risk_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto and self.chek_message.journeyStatistics.auto.intervention_statistics else 0,
# #             "noa_invervention_risk_mpi": self.chek_message.journeyStatistics.noa.intervention_statistics.risk_mpi if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.noa and self.chek_message.journeyStatistics.noa.intervention_statistics else 0,
# #             "noa_invervention_mpi": self.chek_message.journeyStatistics.noa.intervention_statistics.mpi if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.noa and self.chek_message.journeyStatistics.noa.intervention_statistics else 0,
# #             "noa_invervention_risk_cnt": self.chek_message.journeyStatistics.noa.intervention_statistics.risk_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.noa and self.chek_message.journeyStatistics.noa.intervention_statistics else 0,
# #             "noa_auto_mileages": self.chek_message.journeyStatistics.noa.odometer if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.noa else 0,
# #             "noa_auto_mileages_proportion": self.chek_message.journeyStatistics.noa.odometer/(self.chek_message.journeyStatistics.noa.odometer+self.chek_message.journeyStatistics.lcc.odometer) if  self.chek_message.journeyStatistics.noa and self.chek_message.journeyStatistics.lcc else 0,  
# #             "noa_invervention_cnt": self.chek_message.journeyStatistics.noa.intervention_statistics.cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.noa and self.chek_message.journeyStatistics.noa.intervention_statistics else 0,
# #             "lcc_invervention_risk_mpi": self.chek_message.journeyStatistics.lcc.intervention_statistics.risk_mpi if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.lcc and self.chek_message.journeyStatistics.lcc.intervention_statistics else 0,
# #             "lcc_invervention_mpi": self.chek_message.journeyStatistics.lcc.intervention_statistics.mpi if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.lcc and self.chek_message.journeyStatistics.lcc.intervention_statistics else 0,
# #             "lcc_invervention_risk_cnt": self.chek_message.journeyStatistics.lcc.intervention_statistics.risk_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.lcc and self.chek_message.journeyStatistics.lcc.intervention_statistics else 0,
# #             "lcc_auto_mileages": self.chek_message.journeyStatistics.lcc.odometer if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.lcc else 0,
# #             "lcc_auto_mileages_proportion": self.chek_message.journeyStatistics.lcc.odometer/(self.chek_message.journeyStatistics.noa.odometer+self.chek_message.journeyStatistics.lcc.odometer) if  self.chek_message.journeyStatistics.noa and self.chek_message.journeyStatistics.lcc else 0,  
# #             "lcc_invervention_cnt": self.chek_message.journeyStatistics.lcc.intervention_statistics.cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.lcc and self.chek_message.journeyStatistics.lcc.intervention_statistics else 0,
# #             "auto_dcc_max": self.chek_message.journeyStatistics.auto.dcc_max if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_dcc_frequency": self.chek_message.journeyStatistics.auto.dcc_frequency if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_dcc_cnt": self.chek_message.journeyStatistics.auto.dcc_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_dcc_duration": self.chek_message.journeyStatistics.auto.dcc_duration if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_dcc_average_duration": self.chek_message.journeyStatistics.auto.dcc_duration/self.chek_message.journeyStatistics.auto.dcc_cnt if self.chek_message.journeyStatistics.auto and self.chek_message.journeyStatistics.auto.dcc_cnt else 0 ,  
# #             "auto_dcc_average": self.chek_message.journeyStatistics.auto.dcc_average if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_acc_max": self.chek_message.journeyStatistics.auto.acc_max if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_acc_frequency": self.chek_message.journeyStatistics.auto.acc_frequency if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_acc_cnt": self.chek_message.journeyStatistics.auto.acc_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_acc_duration": self.chek_message.journeyStatistics.auto.acc_duration if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "auto_acc_average_duration": self.chek_message.journeyStatistics.auto.acc_duration/self.chek_message.journeyStatistics.auto.acc_cnt if self.chek_message.journeyStatistics.auto.acc_duration and self.chek_message.journeyStatistics.auto.acc_cnt else 0,  # 未在原始数据中找到直接对应字段，设为0
# #             "auto_acc_average": self.chek_message.journeyStatistics.auto.acc_average if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.auto else 0,
# #             "driver_mileages": self.chek_message.journeyStatistics.driver.odometer if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_dcc_max": self.chek_message.journeyStatistics.driver.dcc_max if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_dcc_frequency": self.chek_message.journeyStatistics.driver.dcc_frequency if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_acc_max": self.chek_message.journeyStatistics.driver.acc_max if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_acc_frequency": self.chek_message.journeyStatistics.driver.acc_frequency if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_speed_average": self.chek_message.journeyStatistics.driver.speed_average if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_speed_max": self.chek_message.journeyStatistics.driver.speed_max if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_dcc_cnt": self.chek_message.journeyStatistics.driver.dcc_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "driver_acc_cnt": self.chek_message.journeyStatistics.driver.acc_cnt if self.chek_message.journeyStatistics and self.chek_message.journeyStatistics.driver else 0,
# #             "journey_start_time": "",  # 未在原始数据中找到对应字段，设为空
# #             "journey_end_time": "",  # 未在原始数据中找到对应字段，设为空
# #             "journey_generated_time": "",  # 未在原始数据中找到对应字段，设为空
# #             "journey_status": "",  # 未在原始数据中找到对应字段，设为空
# #             "pdf_name": "",  # 未在原始数据中找到对应字段，设为空
# #             "pdf_path": self.chek_message.description.pdf_file_path if self.chek_message.description else "",
# #             "auto_MBTI": self.chek_message.car.MBTI if self.chek_message.car else "",
# #             "standby_MBTI": "",  # 未在原始数据中找到对应字段，设为空
# #         }
# #         return data
    
# # import com.vehicle.saas.proto.SaasMessageHandle as proto  # 假设已经生成了对应的Python代码

# class ChekMessageParser:
#     def __init__(self, chek_message):
#         self.chek_message = chek_message

#     def parse(self):

#         # print(self.chek_message.journey)
#         data = {
#             # "name": self.chek_message.user.name if self.chek_message.user else "",
#             # "id": self.chek_message.user.id if self.chek_message.user else 0,
#             # "brand": self.chek_message.car.brand if self.chek_message.car else "",
#             # "model": self.chek_message.car.model if self.chek_message.car else "",
#             # "software_config": self.chek_message.car.version if self.chek_message.car else "",
#             # "journey_category": "", 

#             # "polar_star": {
#             #     "urban": {
#             #         "turn_cnt": self.chek_message.journey.polarStarUrban.turn_cnt if self.chek_message.journey.polarStarUrban else 0,
#             #         "turn_pass_cnt": self.chek_message.journey.polarStarUrban.turn_pass_cnt if self.chek_message.journey.polarStarUrban else 0,
#             #         "turn_pass_rate": self.chek_message.journey.polarStarUrban.turn_pass_rate if self.chek_message.journey.polarStarUrban else 0,
#             #         "urban_road_coverage": self.chek_message.journey.polarStarUrban.urban_road_coverage if self.chek_message.journey.polarStarUrban else 0,
#             #         "auto_driving_efficiency": self.chek_message.journey.polarStarUrban.auto_driving_efficiency if self.chek_message.journey.polarStarUrban else 0
#             #     },
#             #     "highway": {
#             #         "lane_change_cnt": self.chek_message.journey.polarStarhighway.lane_change_cnt if self.chek_message.journey.polarStarhighway else 0,
#             #         "lane_change_successful_cnt": self.chek_message.journey.polarStarhighway.lane_change_successful_cnt if self.chek_message.journey.polarStarhighway else 0,
#             #         "up_down_ramps_cnt": self.chek_message.journey.polarStarhighway.up_down_ramps_cnt if self.chek_message.journey.polarStarhighway else 0,
#             #         "up_down_ramps_successful_cnt": self.chek_message.journey.polarStarhighway.up_down_ramps_successful_cnt if self.chek_message.journey.polarStarhighway else 0,
#             #         "construction_scene_cnt": self.chek_message.journey.polarStarhighway.construction_scene_cnt if self.chek_message.journey.polarStarhighway else 0,
#             #         "construction_scene_successful_cnt": self.chek_message.journey.polarStarhighway.construction_scene_successful_cnt if self.chek_message.journey.polarStarhighway else 0,
#             #         "lane_change_rate": self.chek_message.journey.polarStarhighway.lane_change_rate if self.chek_message.journey.polarStarhighway else 0,
#             #         "up_down_ramps_successful_rate": self.chek_message.journey.polarStarhighway.up_down_ramps_successful_rate if self.chek_message.journey.polarStarhighway else 0,
#             #         "construction_scene_successful_rate": self.chek_message.journey.polarStarhighway.construction_scene_successful_rate if self.chek_message.journey.polarStarhighway else 0
#             #     }
#             # },
#             "auto_mileages": self.chek_message.journey.odometer_auto if self.chek_message.journey else 0,
#             "total_mileages": self.chek_message.journey.odometer_total if self.chek_message.journey else 0,
#             "frames": self.chek_message.journey.auto.frames if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_frames": self.chek_message.journey.auto.frames if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "noa_frames": self.chek_message.journey.noa.frames if self.chek_message.journey and self.chek_message.journey.noa else 0,
#             "lcc_frames": self.chek_message.journey.lcc.frames if self.chek_message.journey and self.chek_message.journey.lcc else 0,
#             "driver_frames": self.chek_message.journey.driver.frames if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "auto_speed_average": self.chek_message.journey.auto.speed_average if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_max_speed": self.chek_message.journey.auto.speed_max if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "invervention_risk_proportion": self.chek_message.journey.auto.intervention_risk /self.chek_message.journey.auto.intervention if self.chek_message.journey and self.chek_message.journey.auto.intervention and self.chek_message.journey.auto.intervention_risk else 0,
#             "invervention_mpi": self.chek_message.journey.auto.mpi if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.mpi else 0,
#             "invervention_risk_mpi": self.chek_message.journey.auto.mpi_risk if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.mpi_risk else 0,
#             "invervention_cnt": self.chek_message.journey.auto.intervention if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.intervention else 0,
#             "invervention_risk_cnt": self.chek_message.journey.auto.intervention_risk if self.chek_message.journey and self.chek_message.journey.auto and self.chek_message.journey.auto.intervention_risk else 0,
#             "noa_auto_mileages": self.chek_message.journey.noa.odometer if self.chek_message.journey and self.chek_message.journey.noa else 0,
#             "noa_auto_mileages_proportion": self.chek_message.journey.noa.odometer/(self.chek_message.journey.noa.odometer+self.chek_message.journey.lcc.odometer) if  self.chek_message.journey.noa and self.chek_message.journey.lcc else 0, 
#             "noa_invervention_risk_proportion": self.chek_message.journey.noa.intervention_risk / self.chek_message.journey.noa.intervention if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.intervention and self.chek_message.journey.noa.intervention_risk else 0,
#             "noa_invervention_mpi": self.chek_message.journey.noa.mpi if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.mpi else 0,
#             "noa_invervention_risk_mpi": self.chek_message.journey.noa.mpi_risk if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.mpi_risk else 0,
#             "noa_invervention_cnt": self.chek_message.journey.noa.intervention if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.intervention else 0,
#             "noa_invervention_risk_cnt": self.chek_message.journey.noa.intervention_risk if self.chek_message.journey and self.chek_message.journey.noa and self.chek_message.journey.noa.intervention_risk else 0,
#             "lcc_invervention_risk_proportion": self.chek_message.journey.lcc.intervention_risk / self.chek_message.journey.lcc.intervention if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.intervention and self.chek_message.journey.lcc.intervention_risk else 0,
#             "lcc_invervention_mpi": self.chek_message.journey.lcc.mpi if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.mpi else 0,
#             "lcc_invervention_risk_mpi": self.chek_message.journey.lcc.mpi_risk if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.mpi_risk else 0,
#             "lcc_invervention_cnt": self.chek_message.journey.lcc.intervention if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.intervention else 0,
#             "lcc_invervention_risk_cnt": self.chek_message.journey.lcc.intervention_risk if self.chek_message.journey and self.chek_message.journey.lcc and self.chek_message.journey.lcc.intervention_risk else 0,
#             "lcc_auto_mileages": self.chek_message.journey.lcc.odometer if self.chek_message.journey and self.chek_message.journey.lcc else 0,
#             "lcc_auto_mileages_proportion": self.chek_message.journey.lcc.odometer/(self.chek_message.journey.noa.odometer+self.chek_message.journey.lcc.odometer) if  self.chek_message.journey.noa and self.chek_message.journey.lcc else 0,  
#             "auto_dcc_max": self.chek_message.journey.auto.dcc_max if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_dcc_frequency": self.chek_message.journey.auto.dcc_frequency if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_dcc_cnt": self.chek_message.journey.auto.dcc_cnt if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_dcc_duration": self.chek_message.journey.auto.dcc_duration if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_dcc_average_duration": self.chek_message.journey.auto.dcc_duration/self.chek_message.journey.auto.dcc_cnt if self.chek_message.journey.auto and self.chek_message.journey.auto.dcc_cnt else 0 ,  
#             "auto_dcc_average": self.chek_message.journey.auto.dcc_average if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_acc_max": self.chek_message.journey.auto.acc_max if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_acc_frequency": self.chek_message.journey.auto.acc_frequency if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_acc_cnt": self.chek_message.journey.auto.acc_cnt if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_acc_duration": self.chek_message.journey.auto.acc_duration if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "auto_acc_average_duration": self.chek_message.journey.auto.acc_duration/self.chek_message.journey.auto.acc_cnt if self.chek_message.journey.auto.acc_duration and self.chek_message.journey.auto.acc_cnt else 0,  # 未在原始数据中找到直接对应字段，设为0
#             "auto_acc_average": self.chek_message.journey.auto.acc_average if self.chek_message.journey and self.chek_message.journey.auto else 0,
#             "driver_mileages": self.chek_message.journey.driver.odometer if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_dcc_max": self.chek_message.journey.driver.dcc_max if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_dcc_frequency": self.chek_message.journey.driver.dcc_frequency if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_acc_max": self.chek_message.journey.driver.acc_max if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_acc_frequency": self.chek_message.journey.driver.acc_frequency if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_speed_average": self.chek_message.journey.driver.speed_average if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_speed_max": self.chek_message.journey.driver.speed_max if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_dcc_cnt": self.chek_message.journey.driver.dcc_cnt if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             "driver_acc_cnt": self.chek_message.journey.driver.acc_cnt if self.chek_message.journey and self.chek_message.journey.driver else 0,
#             # "journey_start_time": "",  # 未在原始数据中找到对应字段，设为空
#             # "journey_end_time": "",  # 未在原始数据中找到对应字段，设为空
#             # "journey_generated_time": "",  # 未在原始数据中找到对应字段，设为空
#             # "journey_status": "",  # 未在原始数据中找到对应字段，设为空
#             # "auto_MBTI": self.chek_message.car.MBTI if self.chek_message.car else "",
#             # "standby_MBTI": "",  # 未在原始数据中找到对应字段，设为空
#         }

     
#         return data
    