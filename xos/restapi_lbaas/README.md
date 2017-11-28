You can follow below commands:

# Pre-procedure
Execute the following command to generate service information of XOS Core.
```
docker exec swarmservice_xos_ui_1 python tosca/run.py xosadmin@opencord.org /opt/cord_profile/swarm-node.yaml; pushd /opt/cord/build/platform-install; ansible-playbook -i inventory/swarm-service onboard-lbaas-playbook.yml; popd
```

# Procedure A
```
>> usage
./add_listener.sh
./add_healthmonitor.sh
./add_pool.sh {health_monitor_id}
./add_member.sh {pool_id} {member_ip} {member_port}
./add_member.sh {pool_id} {member_ip} {member_port}
./add_loadbalancer.sh {listener_id} {pool_id}

>> example
./add_listener.sh 
./add_healthmonitor.sh 
./add_pool.sh beb2abd2-e007-4a43-9cc2-d8fde6e1c438
./add_member.sh 66d79361-0fba-488e-bfc8-3c2596723872 10.10.2.241 9001
./add_member.sh 66d79361-0fba-488e-bfc8-3c2596723872 10.10.2.242 9001
./add_loadbalancer.sh 7089f0d9-f59a-41cf-9415-23c5287426fb 66d79361-0fba-488e-bfc8-3c2596723872
```

# Procedure B
This is like a openstack flow 
```
>> usage
./add_loadbalancer.sh
./add_listener.sh
./add_pool.sh
./add_healthmonitor.sh
./update_pool.sh {pool_id} {health_monitor_id}
./add_member.sh {pool_id} {member_ip} {member_port}
./add_member.sh {pool_id} {member_ip} {member_port}
./update_loadbalancer.sh {loadbalancer_id} {listener_id} {pool_id}

>> example
./add_loadbalancer.sh 
./add_listener.sh 
./add_pool.sh 
./add_healthmonitor.sh 
./update_pool.sh 2966c9cb-e22d-4059-9356-e9201278c8a6 a640b75a-d305-499a-b780-aff01ba5171c
./add_member.sh 2966c9cb-e22d-4059-9356-e9201278c8a6 10.10.2.241 9001
./add_member.sh 2966c9cb-e22d-4059-9356-e9201278c8a6 10.10.2.242 9001
./update_loadbalancer.sh 32c9f961-76f0-46a1-93b9-781a7d88ceaf 199b3b1d-8a77-47bd-a26d-0c1058b455b3 2966c9cb-e22d-4059-9356-e9201278c8a6
```
