import re
from datetime import datetime, timedelta, timezone
import falcon
import mysql.connector
import simplejson as json
from core.useractivity import access_control, api_key_control
import config
from core.utilities import int16_to_hhmm


class Reporting:
    @staticmethod
    def __init__():
        """Initializes Class"""
        pass

    @staticmethod
    def on_options(req, resp):
        resp.status = falcon.HTTP_200

    ####################################################################################################################
    # PROCEDURES
    # Step 1: valid parameters
    # Step 2: query the energy storage power station
    # Step 3: query associated containers
    # Step 4: query associated batteries in containers
    # Step 5: query associated grids in containers
    # Step 6: query associated loads in containers
    # Step 7: query associated power conversion systems in containers
    # Step 8: query associated sensors in containers
    # Step 9: query associated points data in containers
    # Step 10: construct the report
    ####################################################################################################################
    @staticmethod
    def on_get(req, resp):
        if 'API-KEY' not in req.headers or \
                not isinstance(req.headers['API-KEY'], str) or \
                len(str.strip(req.headers['API-KEY'])) == 0:
            access_control(req)
        else:
            api_key_control(req)
        print(req.params)
        # this procedure accepts energy storage power station id or uuid
        energy_storage_power_station_id = req.params.get('id')
        energy_storage_power_station_uuid = req.params.get('uuid')

        ################################################################################################################
        # Step 1: valid parameters
        ################################################################################################################
        if energy_storage_power_station_id is None and energy_storage_power_station_uuid is None:
            raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                   description='API.INVALID_ENERGY_STORAGE_POWER_STATION_ID')

        if energy_storage_power_station_id is not None:
            energy_storage_power_station_id = str.strip(energy_storage_power_station_id)
            if not energy_storage_power_station_id.isdigit() or int(energy_storage_power_station_id) <= 0:
                raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                       description='API.INVALID_ENERGY_STORAGE_POWER_STATION_ID')

        if energy_storage_power_station_uuid is not None:
            regex = re.compile(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
            match = regex.match(str.strip(energy_storage_power_station_uuid))
            if not bool(match):
                raise falcon.HTTPError(status=falcon.HTTP_400, title='API.BAD_REQUEST',
                                       description='API.INVALID_ENERGY_STORAGE_POWER_STATION_UUID')

        reporting_start_datetime_utc = datetime.utcnow() - timedelta(days=1)
        reporting_end_datetime_utc = datetime.utcnow()

        ################################################################################################################
        # Step 2: query the energy storage power station
        ################################################################################################################
        cnx_system = mysql.connector.connect(**config.myems_system_db)
        cursor_system = cnx_system.cursor()

        cnx_historical = mysql.connector.connect(**config.myems_historical_db)
        cursor_historical = cnx_historical.cursor()

        query = (" SELECT id, name, uuid "
                 " FROM tbl_contacts ")
        cursor_system.execute(query)
        rows_contacts = cursor_system.fetchall()

        contact_dict = dict()
        if rows_contacts is not None and len(rows_contacts) > 0:
            for row in rows_contacts:
                contact_dict[row[0]] = {"id": row[0],
                                        "name": row[1],
                                        "uuid": row[2]}

        query = (" SELECT id, name, uuid "
                 " FROM tbl_cost_centers ")
        cursor_system.execute(query)
        rows_cost_centers = cursor_system.fetchall()

        cost_center_dict = dict()
        if rows_cost_centers is not None and len(rows_cost_centers) > 0:
            for row in rows_cost_centers:
                cost_center_dict[row[0]] = {"id": row[0],
                                            "name": row[1],
                                            "uuid": row[2]}
        if energy_storage_power_station_id is not None:
            query = (" SELECT id, name, uuid, "
                     "        address, postal_code, latitude, longitude, capacity, "
                     "        contact_id, cost_center_id, svg, description "
                     " FROM tbl_energy_storage_power_stations "
                     " WHERE id = %s ")
            cursor_system.execute(query, (energy_storage_power_station_id,))
            row = cursor_system.fetchone()
        elif energy_storage_power_station_uuid is not None:
            query = (" SELECT id, name, uuid, "
                     "        address, postal_code, latitude, longitude, capacity, "
                     "        contact_id, cost_center_id, svg, description "
                     " FROM tbl_energy_storage_power_stations "
                     " WHERE uuid = %s ")
            cursor_system.execute(query, (energy_storage_power_station_uuid,))
            row = cursor_system.fetchone()

        if row is None:
            cursor_system.close()
            cnx_system.close()
            raise falcon.HTTPError(status=falcon.HTTP_404, title='API.NOT_FOUND',
                                   description='API.ENERGY_STORAGE_POWER_STATION_NOT_FOUND')
        else:
            energy_storage_power_station_id = row[0]
            contact = contact_dict.get(row[8], None)
            cost_center = cost_center_dict.get(row[9], None)
            meta_result = {"id": row[0],
                           "name": row[1],
                           "uuid": row[2],
                           "address": row[3],
                           "postal_code": row[4],
                           "latitude": row[5],
                           "longitude": row[6],
                           "capacity": row[7],
                           "contact": contact,
                           "cost_center": cost_center,
                           "svg": row[10],
                           "description": row[11],
                           "qrcode": 'energystoragepowerstation:' + row[2]}

        point_list = list()
        meter_list = list()

        # query all energy categories in system
        cursor_system.execute(" SELECT id, name, unit_of_measure, kgce, kgco2e "
                              " FROM tbl_energy_categories "
                              " ORDER BY id ", )
        rows_energy_categories = cursor_system.fetchall()
        if rows_energy_categories is None or len(rows_energy_categories) == 0:
            if cursor_system:
                cursor_system.close()
            if cnx_system:
                cnx_system.close()
            raise falcon.HTTPError(status=falcon.HTTP_404,
                                   title='API.NOT_FOUND',
                                   description='API.ENERGY_CATEGORY_NOT_FOUND')
        energy_category_dict = dict()
        for row_energy_category in rows_energy_categories:
            energy_category_dict[row_energy_category[0]] = {"name": row_energy_category[1],
                                                            "unit_of_measure": row_energy_category[2],
                                                            "kgce": row_energy_category[3],
                                                            "kgco2e": row_energy_category[4]}

        ################################################################################################################
        # Step 3: query associated containers
        ################################################################################################################
        # todo: query multiple energy storage containers
        container_list = list()
        cursor_system.execute(" SELECT c.id, c.name, c.uuid "
                              " FROM tbl_energy_storage_power_stations_containers sc, "
                              "      tbl_energy_storage_containers c "
                              " WHERE sc.energy_storage_power_station_id = %s "
                              "      AND sc.energy_storage_container_id = c.id"
                              " LIMIT 1 ",
                              (energy_storage_power_station_id,))
        row_container = cursor_system.fetchone()
        if row_container is not None:
            container_list.append({"id": row_container[0],
                                   "name": row_container[1],
                                   "uuid": row_container[2]})

        ################################################################################################################
        # Step 4: query associated batteries in containers
        ################################################################################################################
        cursor_system.execute(" SELECT p.id, mb.name, p.units, p.object_type  "
                              " FROM tbl_energy_storage_containers_batteries mb, tbl_points p "
                              " WHERE mb.id = %s AND mb.soc_point_id = p.id ",
                              (container_list[0]['id'],))
        row_point = cursor_system.fetchone()
        if row_point is not None:
            point_list.append({"id": row_point[0],
                               "name": row_point[1] + '.SOC',
                               "units": row_point[2],
                               "object_type": row_point[3]})

        cursor_system.execute(" SELECT p.id, mb.name, p.units, p.object_type  "
                              " FROM tbl_energy_storage_containers_batteries mb, tbl_points p "
                              " WHERE mb.id = %s AND mb.power_point_id = p.id ",
                              (container_list[0]['id'],))
        row_point = cursor_system.fetchone()
        if row_point is not None:
            point_list.append({"id": row_point[0],
                               "name": row_point[1] + '.P',
                               "units": row_point[2],
                               "object_type": row_point[3]})

        cursor_system.execute(" SELECT m.id, mb.name, m.energy_category_id  "
                              " FROM tbl_energy_storage_containers_batteries mb, tbl_meters m "
                              " WHERE mb.id = %s AND mb.charge_meter_id = m.id ",
                              (container_list[0]['id'],))
        row_meter = cursor_system.fetchone()
        if row_meter is not None:
            meter_list.append({"id": row_meter[0],
                               "name": row_meter[1] + '.Charge',
                               "energy_category_id": row_meter[2]})

        cursor_system.execute(" SELECT m.id, mb.name, m.energy_category_id  "
                              " FROM tbl_energy_storage_containers_batteries mb, tbl_meters m "
                              " WHERE mb.id = %s AND mb.discharge_meter_id = m.id ",
                              (container_list[0]['id'],))
        row_meter = cursor_system.fetchone()
        if row_meter is not None:
            meter_list.append({"id": row_meter[0],
                               "name": row_meter[1] + '.Discharge',
                               "energy_category_id": row_meter[2]})

        ################################################################################################################
        # Step 5: query associated grids in containers
        ################################################################################################################
        cursor_system.execute(" SELECT p.id, mg.name, p.units, p.object_type  "
                              " FROM tbl_energy_storage_containers_grids mg, tbl_points p "
                              " WHERE mg.id = %s AND mg.power_point_id = p.id ",
                              (container_list[0]['id'],))
        row_point = cursor_system.fetchone()
        if row_point is not None:
            point_list.append({"id": row_point[0],
                               "name": row_point[1] + '.P',
                               "units": row_point[2],
                               "object_type": row_point[3]})

        cursor_system.execute(" SELECT m.id, mg.name, m.energy_category_id  "
                              " FROM tbl_energy_storage_containers_grids mg, tbl_meters m "
                              " WHERE mg.id = %s AND mg.buy_meter_id = m.id ",
                              (container_list[0]['id'],))
        row_meter = cursor_system.fetchone()
        if row_meter is not None:
            meter_list.append({"id": row_meter[0],
                               "name": row_meter[1] + '.Buy',
                               "energy_category_id": row_meter[2]})

        cursor_system.execute(" SELECT m.id, mg.name, m.energy_category_id  "
                              " FROM tbl_energy_storage_containers_grids mg, tbl_meters m "
                              " WHERE mg.id = %s AND mg.sell_meter_id = m.id ",
                              (container_list[0]['id'],))
        row_meter = cursor_system.fetchone()
        if row_meter is not None:
            meter_list.append({"id": row_meter[0],
                               "name": row_meter[1] + '.Sell',
                               "energy_category_id": row_meter[2]})

        ################################################################################################################
        # Step 6: query associated loads in containers
        ################################################################################################################
        cursor_system.execute(" SELECT p.id, ml.name, p.units, p.object_type  "
                              " FROM tbl_energy_storage_containers_loads ml, tbl_points p "
                              " WHERE ml.id = %s AND ml.power_point_id = p.id ",
                              (container_list[0]['id'],))
        row_point = cursor_system.fetchone()
        if row_point is not None:
            point_list.append({"id": row_point[0],
                               "name": row_point[1] + '.P',
                               "units": row_point[2],
                               "object_type": row_point[3]})

        cursor_system.execute(" SELECT m.id, ml.name, m.energy_category_id  "
                              " FROM tbl_energy_storage_containers_loads ml, tbl_meters m "
                              " WHERE ml.id = %s AND ml.meter_id = m.id ",
                              (container_list[0]['id'],))
        row_meter = cursor_system.fetchone()
        if row_meter is not None:
            meter_list.append({"id": row_meter[0],
                               "name": row_meter[1],
                               "energy_category_id": row_meter[2]})

        ################################################################################################################
        # Step 7: query associated power conversion systems
        ################################################################################################################
        cursor_system.execute(" SELECT charge_start_time1_point_id, charge_end_time1_point_id, "
                              "        charge_start_time2_point_id, charge_end_time2_point_id, "
                              "        charge_start_time3_point_id, charge_end_time3_point_id, "
                              "        charge_start_time4_point_id, charge_end_time4_point_id, "
                              "        discharge_start_time1_point_id, discharge_end_time1_point_id, "
                              "        discharge_start_time2_point_id, discharge_end_time2_point_id, "
                              "        discharge_start_time3_point_id, discharge_end_time3_point_id, "
                              "        discharge_start_time4_point_id, discharge_end_time4_point_id, "
                              "        charge_start_time1_command_id, charge_end_time1_command_id, "
                              "        charge_start_time2_command_id, charge_end_time2_command_id, "
                              "        charge_start_time3_command_id, charge_end_time3_command_id, "
                              "        charge_start_time4_command_id, charge_end_time4_command_id, "
                              "        discharge_start_time1_command_id, discharge_end_time1_command_id, "
                              "        discharge_start_time2_command_id, discharge_end_time2_command_id, "
                              "        discharge_start_time3_command_id, discharge_end_time3_command_id, "
                              "        discharge_start_time4_command_id, discharge_end_time4_command_id "
                              " FROM tbl_energy_storage_containers_power_conversion_systems "
                              " WHERE id = %s "
                              " ORDER BY id "
                              " LIMIT 1 ",
                              (container_list[0]['id'],))
        row_point = cursor_system.fetchone()
        if row_point is not None:
            charge_start_time1_point_id = row_point[0]
            charge_end_time1_point_id = row_point[1]
            charge_start_time2_point_id = row_point[2]
            charge_end_time2_point_id = row_point[3]
            charge_start_time3_point_id = row_point[4]
            charge_end_time3_point_id = row_point[5]
            charge_start_time4_point_id = row_point[6]
            charge_end_time4_point_id = row_point[7]
            discharge_start_time1_point_id = row_point[8]
            discharge_end_time1_point_id = row_point[9]
            discharge_start_time2_point_id = row_point[10]
            discharge_end_time2_point_id = row_point[11]
            discharge_start_time3_point_id = row_point[12]
            discharge_end_time3_point_id = row_point[13]
            discharge_start_time4_point_id = row_point[14]
            discharge_end_time4_point_id = row_point[15]
            charge_start_time1_command_id = row_point[16]
            charge_end_time1_command_id = row_point[17]
            charge_start_time2_command_id = row_point[18]
            charge_end_time2_command_id = row_point[19]
            charge_start_time3_command_id = row_point[20]
            charge_end_time3_command_id = row_point[21]
            charge_start_time4_command_id = row_point[22]
            charge_end_time4_command_id = row_point[23]
            discharge_start_time1_command_id = row_point[24]
            discharge_end_time1_command_id = row_point[25]
            discharge_start_time2_command_id = row_point[26]
            discharge_end_time2_command_id = row_point[27]
            discharge_start_time3_command_id = row_point[28]
            discharge_end_time3_command_id = row_point[29]
            discharge_start_time4_command_id = row_point[30]
            discharge_end_time4_command_id = row_point[31]

        cnx_historical = mysql.connector.connect(**config.myems_historical_db)
        cursor_historical = cnx_historical.cursor()
        query = (" SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s "
                 " UNION ALL "
                 " SELECT point_id, actual_value "
                 " FROM tbl_digital_value_latest "
                 " WHERE point_id = %s ")
        cursor_historical.execute(query, (charge_start_time1_point_id, charge_end_time1_point_id,
                                          charge_start_time2_point_id, charge_end_time2_point_id,
                                          charge_start_time3_point_id, charge_end_time3_point_id,
                                          charge_start_time4_point_id, charge_end_time4_point_id,
                                          discharge_start_time1_point_id, discharge_end_time1_point_id,
                                          discharge_start_time2_point_id, discharge_end_time2_point_id,
                                          discharge_start_time3_point_id, discharge_end_time3_point_id,
                                          discharge_start_time4_point_id, discharge_end_time4_point_id))
        rows = cursor_historical.fetchall()
        time_value_dict = dict()
        if rows is not None and len(rows) > 0:
            for row in rows:
                point_id = row[0]
                time_value_dict[point_id] = int16_to_hhmm(row[1])
        charge_start_time1_value = time_value_dict.get(charge_start_time1_point_id)
        charge_end_time1_value = time_value_dict.get(charge_end_time1_point_id)
        charge_start_time2_value = time_value_dict.get(charge_start_time2_point_id)
        charge_end_time2_value = time_value_dict.get(charge_end_time2_point_id)
        charge_start_time3_value = time_value_dict.get(charge_start_time3_point_id)
        charge_end_time3_value = time_value_dict.get(charge_end_time3_point_id)
        charge_start_time4_value = time_value_dict.get(charge_start_time4_point_id)
        charge_end_time4_value = time_value_dict.get(charge_end_time4_point_id)
        discharge_start_time1_value = time_value_dict.get(discharge_start_time1_point_id)
        discharge_end_time1_value = time_value_dict.get(discharge_end_time1_point_id)
        discharge_start_time2_value = time_value_dict.get(discharge_start_time2_point_id)
        discharge_end_time2_value = time_value_dict.get(discharge_end_time2_point_id)
        discharge_start_time3_value = time_value_dict.get(discharge_start_time3_point_id)
        discharge_end_time3_value = time_value_dict.get(discharge_end_time3_point_id)
        discharge_start_time4_value = time_value_dict.get(discharge_start_time4_point_id)
        discharge_end_time4_value = time_value_dict.get(discharge_end_time4_point_id)

        ################################################################################################################
        # Step 8: query associated sensors
        ################################################################################################################
        # todo

        ################################################################################################################
        # Step 10: query associated points data in containers
        ################################################################################################################
        timezone_offset = int(config.utc_offset[1:3]) * 60 + int(config.utc_offset[4:6])
        if config.utc_offset[0] == '-':
            timezone_offset = -timezone_offset

        parameters_data = dict()
        parameters_data['names'] = list()
        parameters_data['timestamps'] = list()
        parameters_data['values'] = list()

        for point in point_list:
            point_values = []
            point_timestamps = []
            if point['object_type'] == 'ENERGY_VALUE':
                query = (" SELECT utc_date_time, actual_value "
                         " FROM tbl_energy_value "
                         " WHERE point_id = %s "
                         "       AND utc_date_time BETWEEN %s AND %s "
                         " ORDER BY utc_date_time ")
                cursor_historical.execute(query, (point['id'],
                                                  reporting_start_datetime_utc,
                                                  reporting_end_datetime_utc))
                rows = cursor_historical.fetchall()

                if rows is not None and len(rows) > 0:
                    for row in rows:
                        current_datetime_local = row[0].replace(tzinfo=timezone.utc) + \
                                                 timedelta(minutes=timezone_offset)
                        current_datetime = current_datetime_local.strftime('%Y-%m-%dT%H:%M:%S')
                        point_timestamps.append(current_datetime)
                        point_values.append(row[1])
            elif point['object_type'] == 'ANALOG_VALUE':
                query = (" SELECT utc_date_time, actual_value "
                         " FROM tbl_analog_value "
                         " WHERE point_id = %s "
                         "       AND utc_date_time BETWEEN %s AND %s "
                         " ORDER BY utc_date_time ")
                cursor_historical.execute(query, (point['id'],
                                                  reporting_start_datetime_utc,
                                                  reporting_end_datetime_utc))
                rows = cursor_historical.fetchall()

                if rows is not None and len(rows) > 0:
                    for row in rows:
                        current_datetime_local = row[0].replace(tzinfo=timezone.utc) + \
                                                 timedelta(minutes=timezone_offset)
                        current_datetime = current_datetime_local.strftime('%Y-%m-%dT%H:%M:%S')
                        point_timestamps.append(current_datetime)
                        point_values.append(row[1])
            elif point['object_type'] == 'DIGITAL_VALUE':
                query = (" SELECT utc_date_time, actual_value "
                         " FROM tbl_digital_value "
                         " WHERE point_id = %s "
                         "       AND utc_date_time BETWEEN %s AND %s "
                         " ORDER BY utc_date_time ")
                cursor_historical.execute(query, (point['id'],
                                                  reporting_start_datetime_utc,
                                                  reporting_end_datetime_utc))
                rows = cursor_historical.fetchall()

                if rows is not None and len(rows) > 0:
                    for row in rows:
                        current_datetime_local = row[0].replace(tzinfo=timezone.utc) + \
                                                 timedelta(minutes=timezone_offset)
                        current_datetime = current_datetime_local.strftime('%Y-%m-%dT%H:%M:%S')
                        point_timestamps.append(current_datetime)
                        point_values.append(row[1])

            parameters_data['names'].append(point['name'] + ' (' + point['units'] + ')')
            parameters_data['timestamps'].append(point_timestamps)
            parameters_data['values'].append(point_values)

        if cursor_system:
            cursor_system.close()
        if cnx_system:
            cnx_system.close()

        if cursor_historical:
            cursor_historical.close()
        if cnx_historical:
            cnx_historical.close()
        ################################################################################################################
        # Step 11: construct the report
        ################################################################################################################
        result = dict()
        result['energy_storage_power_station'] = meta_result
        result['parameters'] = {
            "names": parameters_data['names'],
            "timestamps": parameters_data['timestamps'],
            "values": parameters_data['values']
        }
        result['reporting_period'] = dict()
        result['reporting_period']['names'] = list()
        result['reporting_period']['units'] = list()
        result['reporting_period']['subtotals'] = list()
        result['reporting_period']['increment_rates'] = list()
        result['reporting_period']['timestamps'] = list()
        result['reporting_period']['values'] = list()

        result['schedule'] = dict()
        result['schedule']['charge_start_time1'] = charge_start_time1_value
        result['schedule']['charge_end_time1'] = charge_end_time1_value
        result['schedule']['charge_start_time2'] = charge_start_time2_value
        result['schedule']['charge_end_time2'] = charge_end_time2_value
        result['schedule']['charge_start_time3'] = charge_start_time3_value
        result['schedule']['charge_end_time3'] = charge_end_time3_value
        result['schedule']['charge_start_time4'] = charge_start_time4_value
        result['schedule']['charge_end_time4'] = charge_end_time4_value
        result['schedule']['discharge_start_time1'] = discharge_start_time1_value
        result['schedule']['discharge_end_time1'] = discharge_end_time1_value
        result['schedule']['discharge_start_time2'] = discharge_start_time2_value
        result['schedule']['discharge_end_time2'] = discharge_end_time2_value
        result['schedule']['discharge_start_time3'] = discharge_start_time3_value
        result['schedule']['discharge_end_time3'] = discharge_end_time3_value
        result['schedule']['discharge_start_time4'] = discharge_start_time4_value
        result['schedule']['discharge_end_time4'] = discharge_end_time4_value
        result['schedule']['charge_start_time1_command_id'] = charge_start_time1_command_id
        result['schedule']['charge_end_time1_command_id'] = charge_end_time1_command_id
        result['schedule']['charge_start_time2_command_id'] = charge_start_time2_command_id
        result['schedule']['charge_end_time2_command_id'] = charge_end_time2_command_id
        result['schedule']['charge_start_time3_command_id'] = charge_start_time3_command_id
        result['schedule']['charge_end_time3_command_id'] = charge_end_time3_command_id
        result['schedule']['charge_start_time4_command_id'] = charge_start_time4_command_id
        result['schedule']['charge_end_time4_command_id'] = charge_end_time4_command_id
        result['schedule']['discharge_start_time1_command_id'] = discharge_start_time1_command_id
        result['schedule']['discharge_end_time1_command_id'] = discharge_end_time1_command_id
        result['schedule']['discharge_start_time2_command_id'] = discharge_start_time2_command_id
        result['schedule']['discharge_end_time2_command_id'] = discharge_end_time2_command_id
        result['schedule']['discharge_start_time3_command_id'] = discharge_start_time3_command_id
        result['schedule']['discharge_end_time3_command_id'] = discharge_end_time3_command_id
        result['schedule']['discharge_start_time4_command_id'] = discharge_start_time4_command_id
        result['schedule']['discharge_end_time4_command_id'] = discharge_end_time4_command_id

        resp.text = json.dumps(result)
