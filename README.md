# Projekat 1 (osnova sistema)

Gateway (NestJS): REST API + Swagger/OpenAPI

DataManager (Python gRPC): CRUD + agregacije, upis u PostgreSQL

SensorGenerator: simulira tok senzorskih podataka slanjem na Gateway

# Projekat 2 (MQTT event-driven)

Mosquitto MQTT broker

DataManager nakon upisa u bazu publikuje poruke na MQTT topic: iot/readings

EventManager subscribe na iot/readings, detektuje pragove i publikuje događaje na iot/events

MQTT Client subscribe na iot/events (prikaz događaja)

# Projekat 3 (ML + NATS)

MLaaS (FastAPI + scikit-learn): REST /predict za inferenciju (model treniran lokalno i spakovan u image)

Analytics subscribe na iot/readings, pravi window feature-e, zove MLaaS i publikuje predikcije na NATS subject iot.predictions

NATS broker

MqttNats aplikacija: prikazuje MQTT evente (iot/events) i NATS predikcije (iot.predictions)

# Pokretanje
U root folder izvrsiti:

`docker compose up --build`

mqttclient se pokrece tako sto se udje u navedeni folder i izvrse komande iz bash.txt
