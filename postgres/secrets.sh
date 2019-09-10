kubectl create secret generic influxdb-ha-creds \
  --from-literal=INFLUXDB_DATABASE=ha \
  --from-literal=INFLUXDB_USERNAME=root \
  --from-literal=INFLUXDB_PASSWORD=root \
  --from-literal=INFLUXDB_HOST=influxdb -n homeautomation
