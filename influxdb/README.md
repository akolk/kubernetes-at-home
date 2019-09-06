# kubernetes-at-home

kubectl create secret generic influxdb-ha-creds \
        --from-literal=INFLUXDB_DATABASE=<db> \
        --from-literal=INFLUXDB_USERNAME=<username> \
        --from-literal=INFLUXDB_PASSWORD=<password> \
        --from-literal=INFLUXDB_HOST=influxdb -n homeautomation
