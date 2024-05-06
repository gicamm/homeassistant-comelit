# How to debug with the mqtt client

## Prerequisite 
- Install the mqtt client (i.e. mosquito)

## Subscribe to the topic
Subscribe to the topic. Any reply will be available there.
Note that you should replace the IP address, port and serial number of the Comelit HUB.
```
mosquitto_sub -v -h $IP -p $PORT -u "hsrv-user" -P "sf1nE9bjPc" -t 'HSrv/$SERIAL/tx/gc'
```

## Login

### Announce
```
mosquitto_pub -h $IP -p $PORT -u "hsrv-user" -P "sf1nE9bjPc" -t 'HSrv/$SERIAL/rx/gc' -m '{"req_type": 13, "req_sub_type": -1, "agent_type": 0}'
```
Get the agent ID from the response and use it later.

### Get the session token
Note that you should replace the IP address, port, serial number of the Comelit HUB, the agent id the credentials.
```
mosquitto_pub -h $IP -p $PORT -u "hsrv-user" -P "sf1nE9bjPc" -t 'HSrv/$SERIAL/rx/gc' -m '{"req_type": 5, "req_sub_type": -1, "agent_type": 0, "user_name": $USERNAME,"password": $PWD, "agent_id":$AGENT_ID}'
```

#### Read the session ID from the response
```
HSrv/$SERIAL/tx/gc {"req_type":5,"req_sub_type":-1,"seq_id":0,"req_result":0,"uid":".....","sessiontoken":"......"}
```

## Turn light ON
Use this session ID and the agent ID to publish messages
```
mosquitto_pub -h $IP -p $PORT -u "hsrv-user" -P "sf1nE9bjPc" -t 'HSrv/$SERIAL/rx/gc' -m '{"req_type": 1, "req_sub_type": 3, "obj_id": "DOM#LT#24.1", "act_type": 0, "act_params": [1], "seq_id": 8321, "agent_id": $AGENT_ID, "sessiontoken": $SESSION_TOKEN}'
```

## Get the status
```
mosquitto_pub -h $IP -p $PORT -u "hsrv-user" -P "sf1nE9bjPc" -t 'HSrv/$SERIAL/rx/gc' -m '{"req_type": 0, "req_sub_type": -1,  "obj_id": "GEN#17#13#1", "detail_level": 1, "seq_id": 8321, "agent_id": $AGENT_ID, "sessiontoken": $SESSION_TOKEN}'
```

You receive a long reply message
