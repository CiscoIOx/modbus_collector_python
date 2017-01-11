freeboard: https://freeboard.io/board/-pu4zg
dweet_name: modbus-device 

curl -i https://dweet.io/listen/for/dweets/from/modbus_device
curl -v1 -k -H "Content-Type: application/json" -X POST -d '{"coil":"True"}' https://localhost:9000/display
