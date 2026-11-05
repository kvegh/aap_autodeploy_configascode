"""Strict supplemental AAP ownership, static NM readback and complete teardown."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import yaml
from ansible.errors import AnsibleFilterError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.plugins.action import ActionBase
from test_aap_final_release import fixture as aap_fixture
from test_aap_hypervisor_access import fixture as native_fixture
from test_decommission_guest_access import RETIRE
from test_decommission_guest_access import fixture as legacy_fixture
import test_guest_release as transaction

keys = transaction.keys
native = keys._management


def fixture():
    guest, pin, main, shared, hactar, allocation = aap_fixture()
    pin['isolation_bridges'].append('vmbr1')
    guest['route']['hypervisor'] = deepcopy(pin)
    allocation['aap_vm_allocation']['reservations']['selected-request']['instance_route'] = deepcopy(guest['route'])
    for rows in (main['autodeploy_configuration']['inventories'], shared['host_inventory_configuration']['hosts'],
                 hactar['controller_hosts_hactar_recovery']):
        for row in rows:
            values = keys.inventory_variables(row)
            if 'aap_hypervisor_pin' in values:
                values['aap_hypervisor_pin'] = deepcopy(pin)
            for name in ('isolation_policy', 'hactar_isolation_policy'):
                if name in values:
                    values[name]['bridges'] = deepcopy(pin['isolation_bridges'])
            keys.set_inventory_variables(row, values)
    nic = {'owner_project_id': 'disconnected-windows-patching', 'network': 'windows-isolated', 'bridge': 'vmbr1',
           'address': '192.168.80.10', 'mac': '52:54:00:80:00:10',
           'connection_uuid': '11111111-2222-3333-4444-555555555555', 'connection_name': 'windows-demo-v07',
           'attachment_created': True, 'connection_created': True}
    observed = {'uuid': nic['connection_uuid'], 'name': nic['connection_name'], 'mac': nic['mac'],
                'addresses': [nic['address'] + '/24'], 'gateway': '', 'dns': [], 'never_default': True, 'autoconnect': True,
                'ipv4_method': 'manual', 'ipv4_ignore_auto_dns': True, 'ipv6_method': 'disabled',
                'ipv6_never_default': True, 'ipv6_ignore_auto_dns': True}
    guest.update(supplemental_interface=nic, supplemental_state='present',
                 connection_readback={'machine_id': guest['guest_machine_id'], 'connections': [observed]})
    return guest, pin, main, shared, hactar, allocation


def planned():
    guest, pin, main, shared, hactar, allocation = fixture()
    context = keys.supplemental_interface_context(main, shared, allocation, guest, pin)
    transition = {name: context[name] for name in ('previous_policy', 'desired_policy', 'previous_resource', 'desired_resource')}
    return guest, pin, main, shared, hactar, allocation, context, transition


def actual():
    guest, pin, main, shared, hactar, allocation, context, transition = planned()
    _, state, *_ = native_fixture()
    state['policy'] = deepcopy(context['previous_policy'])
    nic = guest['supplemental_interface']
    extra = ('<interface type="network"><mac address="%s"/><source network="%s"/>'
             '<alias name="ua-windows-%s"/><model type="virtio"/></interface>') % (nic['mac'], nic['network'], nic['connection_uuid'])
    for scope, xml in state['domains'][guest['route']['vm_name']].items():
        state['domains'][guest['route']['vm_name']][scope] = xml.replace('</devices>', extra + '</devices>')
    network = ('<network><name>windows-isolated</name><bridge name="vmbr1"/>'
               '<ip address="192.168.80.1" netmask="255.255.255.0"><dhcp>'
               '<range start="192.168.80.100" end="192.168.80.200"/></dhcp></ip></network>')
    state['networks'][nic['network']] = network
    state['supplemental_network_definitions'] = {nic['network']: {'persistent': network, 'current': network}}
    request = {'operation': 'apply', 'mode': 'supplemental_interface', 'guest': guest,
               'hypervisor': pin, 'transition': transition, 'check_mode': False}
    return request, state, (main, shared, hactar, allocation, context)


class SupplementalInterfaceTests(unittest.TestCase):
    def test_live_legacy_primary_reservations_reuse_the_already_verified_native_identity(self):
        policy,retirement,route,related,xmls,definitions=legacy_fixture()
        self.assertNotIn('aap',related)
        mac='52:54:00:12:34:56'
        dhcp='<host mac="%s" name="%s" ip="%s"/>'%(mac,route['vm_name'],route['vm_ip'])
        dns='<host ip="%s"><hostname>%s</hostname></host>'%(route['vm_ip'],route['vm_name'])
        xml=definitions['isolated'].replace('</network>','<ip address="192.168.70.1"><dhcp>'+dhcp+'</dhcp></ip><dns>'+dns+'</dns></network>')
        networks={'isolated':{'current':xml,'persistent':xml}}
        proof=RETIRE.guest_access_plan(policy,retirement,route,related,xmls,networks)
        before=deepcopy((networks,related,xmls,proof))
        plan=RETIRE.reservation_plan(networks,route,related,xmls,proof)
        self.assertEqual(len(plan['reservations']),4)
        self.assertNotIn('verified',proof['live_primary_identity'])
        self.assertEqual((networks,related,xmls,proof),before)
        self.assertFalse(RETIRE.reservation_plan(plan['after'],route,related,xmls,proof)['reservations'])
        # Preserve accepted legacy bridge-backed guests without inventing a
        # libvirt network association for a reservation they do not own.
        bridge_xmls=deepcopy(xmls)
        bridge_xmls[route['vm_name']]=bridge_xmls[route['vm_name']].replace('interface type="network"','interface type="bridge"').replace('source network="isolated"','source bridge="vmbr0"')
        empty_networks={name:{'current':value,'persistent':value} for name,value in definitions.items()}
        bridge_proof=RETIRE.guest_access_plan(policy,retirement,route,related,bridge_xmls,empty_networks)
        self.assertFalse(RETIRE.reservation_plan(empty_networks,route,related,bridge_xmls,bridge_proof)['reservations'])
        for variant in ('mac','ip','name','network','missing-proof','missing-xml','changed-live-mac','changed-plan'):
            bad=deepcopy(networks);live=deepcopy(xmls);verified=deepcopy(proof)
            if variant=='mac':bad['isolated']['persistent']=xml.replace(mac,'52:54:00:12:34:99')
            elif variant=='ip':bad['isolated']['persistent']=xml.replace('ip="'+route['vm_ip']+'"','ip="192.168.70.99"',1)
            elif variant=='name':bad['isolated']['persistent']=xml.replace('name="'+route['vm_name']+'"','name="foreign"')
            elif variant=='network':
                bad['foreign']={'persistent':xml.replace('<name>isolated</name>','<name>foreign</name>')}
            elif variant=='missing-proof':verified=None
            elif variant=='missing-xml':live={}
            elif variant=='changed-live-mac':live[route['vm_name']]=live[route['vm_name']].replace(mac,'52:54:00:12:34:99')
            else:verified['live_primary_identity']['network']='foreign'
            with self.subTest(variant=variant),self.assertRaises(AnsibleFilterError):
                RETIRE.reservation_plan(bad,route,related,live,verified)

    def test_absent_legacy_vm_and_missing_record_cannot_authorize_named_reservation_cleanup(self):
        policy,retirement,route,related,xmls,definitions=legacy_fixture()
        mac='52:54:00:12:34:56'
        host='<host mac="%s" name="%s" ip="%s"/>'%(mac,route['vm_name'],route['vm_ip'])
        xml=definitions['isolated'].replace('</network>','<ip address="192.168.70.1"><dhcp>'+host+'</dhcp></ip></network>')
        networks={'isolated':{'current':xml,'persistent':xml}}
        for name in (route['vm_name'],route['aap_hostname'].removeprefix('https://'),'unrelated'):
            candidate=deepcopy(networks)
            candidate['isolated']['persistent']=xml.replace('name="'+route['vm_name']+'"','name="'+name+'"')
            with self.subTest(name=name),self.assertRaises(AnsibleFilterError):
                RETIRE.reservation_plan(candidate,route,related,{},None)

    def test_plan_only_native_role_loads_publisher_and_never_reaches_host_operations(self):
        root = Path(__file__).resolve().parents[1]
        for native_mode in ('true', 'false'):
            with self.subTest(native=native_mode), tempfile.TemporaryDirectory(prefix='supplemental-plan-role-') as temporary:
                path = Path(temporary)
                play = path / 'plan.yml'
                play.write_text(yaml.safe_dump([{'hosts':'localhost','connection':'local','gather_facts':False,
                    'vars':{'recovery_release_guest':{},'recovery_release_hypervisor':{},
                            'recovery_release_trust_file':str(path/'unused-trust'),
                            'recovery_release_operation':'aap_supplemental_interface'},
                    'tasks':[{'ansible.builtin.include_role':{'name':str(root/'roles/recovery_guest_release'),
                                                            'tasks_from':'plan'}}]}],sort_keys=False))
                env = dict(os.environ, ANSIBLE_HOME=str(path/'home'), ANSIBLE_LOCAL_TEMP=str(path/'local'),
                           ANSIBLE_REMOTE_TEMP=str(path/'remote'), ANSIBLE_JINJA2_NATIVE=native_mode)
                for name in ('CAC_GIT_TOKEN','AAP_CAC_SOURCE_TOKEN','AAP_CAC_SOURCE_URL'): env.pop(name,None)
                result = subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(play)],
                                        env=env,cwd=root,capture_output=True,text=True,timeout=45)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Preflight the source job',result.stdout)
                self.assertNotIn('Allocate protected temporary',result.stdout)
                self.assertNotIn("couldn't resolve module",result.stdout+result.stderr)
                self.assertNotIn('No module named',result.stdout+result.stderr)

    def test_remaining_owner_proof_preserves_unrelated_windows_nics_and_aap_extra(self):
        from test_windows_guest_lifecycle import source_fixture
        guest,pin,main,shared,hactar,allocation,context,_ = planned()
        shared = keys.supplemental_interface_capture(shared,context,'shared')
        allocation = keys.supplemental_interface_capture(allocation,context,'allocation')
        windows = source_fixture()[0]
        release = keys.guest_release_context(main,shared,windows,pin)
        main = keys.guest_release_inventory_capture(main,release,'autodeploy')
        shared = keys.guest_release_inventory_capture(shared,release,'shared')
        hactar = keys.guest_release_inventory_capture(hactar,release,'hactar')
        source = transaction.Source(main,shared,hactar)
        proof = keys.source_related_resources(source,shared,allocation['aap_vm_allocation'],guest['route']['vm_name'])
        expected = [{'bridge':nic['bridge'],'ipv4':nic['address'],'mac':nic['mac']}
                    for nic in windows['interfaces']+[guest['supplemental_interface']]]
        self.assertTrue(all(identity in proof['policy_owners'] for identity in expected))
        self.assertFalse(source.calls)

    def test_related_linux_guest_cannot_borrow_the_aap_supplemental_declaration(self):
        request, state, docs = actual()
        main, shared, hactar, allocation, context = docs
        guest = deepcopy(request['guest']['primary'])
        guest.update(supplemental_interfaces=[request['guest']['supplemental_interface']],
                     uuid='99999999-2222-3333-4444-555555555555', address='192.168.70.20',
                     disk='/opt/vms/zabbix-v07.disk.qcow2', vm_name='zabbix-v07')
        resources = {'aap': request['transition']['desired_resource'], 'zabbix': guest}
        route = request['guest']['route']
        retirement = RETIRE.resources(route, 'example.invalid', '/opt/vms', resources)
        networks = {name: {'current': xml, 'persistent': xml} for name, xml in state['networks'].items()}
        with self.assertRaises(AnsibleFilterError): RETIRE.guest_access_plan(state['policy'],retirement,route,resources,{},networks)
        with self.assertRaises(AnsibleFilterError): RETIRE.reservation_plan(networks,route,resources)
        record = allocation['aap_vm_allocation']['reservations']['selected-request']
        with self.assertRaises(ValueError): keys.isolation_retirement_context(record,route['vm_name'],route['aap_hostname'],
            {'previous_policy':state['policy'],'desired_policy':state['policy'],'identities':[]},{'zabbix':guest})

    def test_other_guest_collision_checks_include_aap_supplemental_nics(self):
        request, *_ = actual()
        old = request['transition']['desired_resource']
        other = dict(old, uuid='99999999-2222-3333-4444-555555555555', disk='/opt/vms/foreign.disk.qcow2',
                     address='192.168.80.10', mac='52:54:00:00:00:99')
        other.pop('supplemental_interfaces')
        self.assertTrue(keys.guest_resource_conflicts(old,other))

    def test_plan_is_readonly_and_publish_changes_only_same_two_saved_records(self):
        guest, pin, main, shared, hactar, allocation, context, transition = planned()
        original = deepcopy((main, shared, hactar, allocation))
        context = keys.supplemental_interface_context(main, shared, allocation, guest, pin, transition)
        desired = {kind: keys.supplemental_interface_capture(value, context, kind) for kind, value in
                   {'autodeploy': main, 'shared': shared, 'hactar': hactar, 'allocation': allocation}.items()}
        self.assertEqual((main, shared, hactar, allocation), original)
        self.assertEqual(desired['autodeploy'], main)
        self.assertEqual(desired['hactar'], hactar)
        record = desired['allocation']['aap_vm_allocation']['reservations']['selected-request']
        self.assertEqual(record['instance_route'], guest['route'])
        self.assertEqual(record['instance_resources']['aap'], transition['desired_resource'])
        source = transaction.Source(main, shared, hactar)
        operations = keys.source_supplemental_interface_operations(source, desired['shared'], main, hactar, context)
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0][0], 'PATCH')
        self.assertTrue(operations[0][1].startswith('hosts/'))
        method, path, body = operations[0]
        source.request(method, path, body)
        self.assertEqual(keys.source_supplemental_interface_operations(source, desired['shared'], main, hactar, context), [])
        self.assertEqual(context['previous_policy'], context['desired_policy'])

    def test_precreation_plan_does_not_claim_actual_connection_or_accept_changed_primary(self):
        guest, pin, main, shared, _, allocation = fixture()
        guest['connection_readback']['connections'] = []
        context = keys.supplemental_interface_context(main, shared, allocation, guest, pin)
        with self.assertRaises(ValueError):
            keys.supplemental_interface_context(main, shared, allocation, guest, pin,
                {name: context[name] for name in ('previous_policy','desired_policy','previous_resource','desired_resource')})
        for field, value in (('uuid', '99999999-2222-3333-4444-555555555555'), ('disk', '/foreign'),
                             ('address', '192.168.70.99'), ('mac', '52:54:00:00:00:99')):
            changed = deepcopy(guest);changed['primary'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                keys.supplemental_interface_context(main, shared, allocation, changed, pin)
        for field,value in (('hypervisor_host','foreign'),('aap_instance_number','007'),('aap_instance_number',True)):
            guest,pin,main,shared,_,allocation=fixture()
            row=next(row for row in shared['host_inventory_configuration']['hosts'] if keys.aap_inventory_owner(row,guest['route']['vm_name']))
            values=keys.inventory_variables(row);values[field]=value;keys.set_inventory_variables(row,values)
            with self.subTest(field=field),self.assertRaises(ValueError):
                keys.supplemental_interface_context(main,shared,allocation,guest,pin)

    def test_nic_declaration_rejects_foreign_owner_false_creation_and_primary_overlap(self):
        for field, value in (('owner_project_id', 'foreign'), ('attachment_created', False), ('connection_created', False),
                             ('connection_uuid', 'foreign'), ('connection_name', 'with space'), ('address', '127.0.0.1'),
                             ('mac', '01:00:00:00:00:01'), ('network', 'isolated'), ('bridge', 'vmbr0')):
            guest, pin, main, shared, _, allocation = fixture()
            guest['supplemental_interface'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                keys.supplemental_interface_context(main, shared, allocation, guest, pin)

    def test_authenticated_nm_readback_rejects_changed_or_unsafe_settings(self):
        for field, value in (('uuid', '99999999-2222-3333-4444-555555555555'), ('mac','52:54:00:80:00:99'),
                             ('name', 'foreign'), ('addresses',['192.168.80.99/24']), ('gateway','192.168.80.1'),
                             ('dns',['192.168.80.1']), ('never_default',False), ('autoconnect',False),
                             ('ipv4_method','auto'), ('ipv4_ignore_auto_dns',False), ('ipv6_method','auto'),
                             ('ipv6_never_default',False), ('ipv6_ignore_auto_dns',False)):
            guest, *_ = fixture();guest['connection_readback']['connections'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): native.connection_readback(guest)
        guest, *_ = fixture();guest['connection_readback']['machine_id'] = 'b' * 32
        with self.assertRaises(ValueError): native.connection_readback(guest)
        guest, *_ = fixture();guest['connection_readback']['connections'].append(
            dict(guest['connection_readback']['connections'][0], uuid='99999999-2222-3333-4444-555555555555'))
        with self.assertRaises(ValueError): native.connection_readback(guest)

    def test_native_complete_nic_and_connection_proof_changes_no_permissions(self):
        request, state, _ = actual();before = deepcopy((request,state))
        change = transaction.load('supplemental_native_runtime', 'src/aap_guest_release.py').plan(request,state)
        self.assertEqual((request,state),before)
        self.assertFalse(change['changed']);self.assertTrue(change['ownership_verified'])
        self.assertEqual(change['previous_policy'], change['desired_policy'])
        # Static secondary addresses need no fake DHCP lease; any extra observed lease must be exact.
        state['leases'] += '\n52:54:00:80:00:10 ipv4 192.168.80.10/24'
        self.assertFalse(transaction.load('supplemental_native_runtime2', 'src/aap_guest_release.py').plan(request,state)['changed'])

    def test_native_rejects_unrecorded_tampered_or_missing_current_persistent_nics(self):
        runtime = transaction.load('supplemental_native_runtime3', 'src/aap_guest_release.py')
        for variant in ('current','persistent','third','missing-state','network','forward','dhcp','subnet',
                        'persistent-dhcp','persistent-subnet','foreign-dns','foreign-lease',
                        'marker-current','marker-persistent','model-current','model-persistent'):
            request,state,_ = actual();name=request['guest']['route']['vm_name'];nic=request['guest']['supplemental_interface']
            if variant in ('current','persistent'):
                state['domains'][name][variant]=state['domains'][name][variant].replace(nic['mac'],'52:54:00:80:00:99')
            elif variant=='third': state['domains'][name]['current']=state['domains'][name]['current'].replace('</devices>','<interface type="network"><mac address="52:54:00:80:00:99"/><source network="windows-isolated"/></interface></devices>')
            elif variant=='missing-state': del state['domains'][name]['persistent']
            elif variant=='network': state['supplemental_network_definitions'][nic['network']]['persistent']=state['networks'][nic['network']].replace('vmbr1','foreign')
            elif variant=='forward': state['supplemental_network_definitions'][nic['network']]['persistent']=state['networks'][nic['network']].replace('</network>','<forward mode="nat"/></network>')
            elif variant=='dhcp': request['guest']['connection_readback']['connections'][0]['addresses']=['192.168.80.150/24'];request['guest']['supplemental_interface']['address']='192.168.80.150';request['transition']['desired_resource']['supplemental_interfaces'][0]['address']='192.168.80.150'
            elif variant=='subnet': request['guest']['connection_readback']['connections'][0]['addresses']=['192.168.80.10/16']
            elif variant=='persistent-dhcp': state['supplemental_network_definitions'][nic['network']]['persistent']=state['networks'][nic['network']].replace('192.168.80.100','192.168.80.2')
            elif variant=='persistent-subnet': state['supplemental_network_definitions'][nic['network']]['persistent']=state['networks'][nic['network']].replace('255.255.255.0','255.255.0.0')
            elif variant=='foreign-dns': state['supplemental_network_definitions'][nic['network']]['persistent']=state['networks'][nic['network']].replace('</network>','<dns><host ip="192.168.80.10"><hostname>foreign</hostname></host></dns></network>')
            elif variant.startswith('marker-'):
                scope=variant.split('-',1)[1];state['domains'][name][scope]=state['domains'][name][scope].replace('ua-windows-'+nic['connection_uuid'],'ua-unowned')
            elif variant.startswith('model-'):
                scope=variant.split('-',1)[1];state['domains'][name][scope]=state['domains'][name][scope].replace('type="virtio"','type="e1000"')
            else: state['leases']+='\n52:54:00:80:00:99 ipv4 192.168.80.10/24'
            with self.subTest(variant=variant),self.assertRaises(ValueError): runtime.plan(request,state)

    def test_final_aap_release_verifies_extra_but_releases_only_primary(self):
        request,state,_=actual();runtime=transaction.load('supplemental_final_runtime','src/aap_guest_release.py')
        guest=request['guest'];guest={key:guest[key] for key in ('kind','route','guest_machine_id')}
        guest['primary']=request['transition']['desired_resource']
        previous=state['policy'];desired=deepcopy(previous)
        primary=guest['primary'];identity={'bridge':primary['bridge'],'ipv4':primary['address'],'mac':primary['mac']}
        desired.setdefault('released_clients',[]).append(identity)
        result=runtime.plan({'operation':'apply','guest':guest,'hypervisor':request['hypervisor'],
                            'transition':{'previous_policy':previous,'desired_policy':desired},'check_mode':False},state)
        self.assertEqual(result['desired_policy'],desired)
        self.assertNotIn({'bridge':'vmbr1','ipv4':'192.168.80.10','mac':'52:54:00:80:00:10'},desired['released_clients'])

    def test_absence_requires_exact_nic_and_nm_connection_gone_and_preserves_primary(self):
        request,state,docs=actual();main,shared,hactar,allocation,context=docs
        allocation=keys.supplemental_interface_capture(allocation,context,'allocation')
        shared=keys.supplemental_interface_capture(shared,context,'shared')
        guest=request['guest'];guest['primary']=deepcopy(request['transition']['desired_resource']);guest['supplemental_state']='absent'
        guest['connection_readback']['connections']=[]
        remove=keys.supplemental_interface_context(main,shared,allocation,guest,request['hypervisor'])
        transition={key:remove[key] for key in ('previous_policy','desired_policy','previous_resource','desired_resource')}
        request['transition']=transition
        runtime=transaction.load('supplemental_remove_runtime','src/aap_guest_release.py')
        with self.assertRaises(ValueError): runtime.plan(request,state)
        for scope,xml in state['domains'][guest['route']['vm_name']].items():
            root=ET.fromstring(xml)
            for item in root.findall('./devices/interface'):
                if item.find('mac').get('address')==guest['supplemental_interface']['mac']: root.find('devices').remove(item)
            state['domains'][guest['route']['vm_name']][scope]=ET.tostring(root,encoding='unicode')
        self.assertTrue(runtime.plan(request,state)['ownership_verified'])
        removed=keys.supplemental_interface_capture(allocation,remove,'allocation')
        self.assertEqual(removed['aap_vm_allocation']['reservations']['selected-request']['instance_resources']['aap'],transition['desired_resource'])
        self.assertTrue(native.same_primary(transition['previous_resource'],transition['desired_resource']))

    def test_full_decommission_remembers_every_nic_after_domain_absence(self):
        request,state,docs=actual();main,shared,hactar,allocation,context=docs
        route=request['guest']['route'];resource=request['transition']['desired_resource'];nic=request['guest']['supplemental_interface']
        resources={'aap':resource}
        retirement=RETIRE.resources(route,'example.invalid','/opt/vms',resources)
        networks={name:dict(current=xml,persistent=xml) for name,xml in state['networks'].items()}
        # Other use-case VMs may be absent, but both AAP interfaces remain fully recorded.
        policy=deepcopy(state['policy']);policy.setdefault('http_clients',[]).append({'bridge':nic['bridge'],'ipv4':nic['address'],'mac':nic['mac']})
        xmls={route['vm_name']:state['domains'][route['vm_name']]['current']}
        persistent={route['vm_name']:state['domains'][route['vm_name']]['persistent']}
        plan=RETIRE.guest_access_plan(policy,retirement,route,resources,xmls,networks,persistent_xmls=persistent)
        self.assertEqual(len(plan['identities']),2);self.assertNotIn('http_clients',plan['desired_policy'])
        for scope in ('current','persistent'):
            bad_current,bad_saved=deepcopy(xmls),deepcopy(persistent)
            bad=bad_current if scope=='current' else bad_saved
            bad[route['vm_name']]=bad[route['vm_name']].replace('ua-windows-'+nic['connection_uuid'],'ua-unowned')
            with self.subTest(scope=scope),self.assertRaises(AnsibleFilterError):
                RETIRE.guest_access_plan(policy,retirement,route,resources,bad_current,networks,persistent_xmls=bad_saved)
        absent=RETIRE.guest_access_plan(policy,retirement,route,resources,{},networks)
        self.assertEqual(absent['identities'],plan['identities'])
        self.assertEqual(RETIRE.guest_networks({},resources),['isolated','windows-isolated'])
        record=keys.supplemental_interface_capture(allocation,context,'allocation')['aap_vm_allocation']['reservations']['selected-request']
        retired=keys.isolation_retirement_context(record,route['vm_name'],route['aap_hostname'],
             {key:plan[key] for key in ('previous_policy','desired_policy','identities')})
        self.assertEqual(retired['identities'],plan['identities'])

    def test_exact_dhcp_dns_cleanup_preserves_foreign_records_and_supports_partial_retry(self):
        request,state,_=actual();route=request['guest']['route'];primary=request['transition']['desired_resource']
        reservation='<host mac="%s" name="%s" ip="%s"/>'%(primary['mac'],route['vm_name'],primary['address'])
        dns='<host ip="%s"><hostname>%s</hostname></host>'%(primary['address'],route['vm_name'])
        foreign='<host mac="52:54:00:00:00:99" name="unrelated" ip="192.168.70.99"/>'
        xml=state['networks']['isolated'].replace('</network>','<ip address="192.168.70.1"><dhcp>'+reservation+foreign+'</dhcp></ip><dns>'+dns+'</dns></network>')
        networks={'isolated':{'current':xml,'persistent':xml},'windows-isolated':dict(state['supplemental_network_definitions']['windows-isolated'])}
        before=deepcopy(networks);plan=RETIRE.reservation_plan(networks,route,{'aap':primary})
        self.assertEqual(networks,before);self.assertEqual(len(plan['reservations']),4)
        self.assertTrue(RETIRE.reservation_matches(plan['after'],plan))
        self.assertTrue(all('unrelated' in xml for xml in plan['after']['isolated'].values()))
        retry=deepcopy(networks);retry['isolated']['current']=plan['after']['isolated']['current']
        second=RETIRE.reservation_plan(retry,route,{'aap':primary})
        self.assertEqual(len(second['reservations']),2)
        self.assertFalse(RETIRE.reservation_plan(plan['after'],route,{'aap':primary})['reservations'])
        bad=deepcopy(networks);bad['isolated']['persistent']=xml.replace('52:54:00:12:34:56','52:54:00:00:00:98')
        with self.assertRaises(AnsibleFilterError): RETIRE.reservation_plan(bad,route,{'aap':primary})
        bad=deepcopy(plan['after']);bad['isolated']['current']=bad['isolated']['current'].replace('unrelated','changed')
        self.assertFalse(RETIRE.reservation_matches(bad,plan))


class SupplementalPublicationTests(unittest.TestCase):
    def test_actual_encrypted_git_cas_interrupted_source_retry_and_exact_removal(self):
        module = transaction.load('supplemental_action', 'action_plugins/aap_publish_instance_keys.py')
        guest,pin,main,shared,hactar,allocation=fixture()
        source=transaction.Source(main,shared,hactar)
        secret=VaultSecret(b'synthetic-fixture-password')
        vault=VaultLib([('default',secret)])
        docs={'vaults/cac/aap_autodeploy_configascode-cac-vault.yml':main,'cac/host_inventory.yml':shared,
              'cac/hactar_recovery.yml':hactar,'state/aap_vm_allocations_vault.yml':allocation}
        real_run=subprocess.run
        with tempfile.TemporaryDirectory(prefix='aap-supplemental-publication-') as temporary:
            root=Path(temporary);remote=root/'remote.git';seed=root/'seed';seed.mkdir();project=root/'project';project.mkdir()
            def git(path,*args):
                return real_run(['git','-C',str(path),*args],check=True,text=True,capture_output=True)
            real_run(['git','init','--bare','--initial-branch=main',str(remote)],check=True,capture_output=True)
            git(seed,'init','--initial-branch=main')
            for name,value in docs.items():
                path=seed/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(vault.encrypt(yaml.dump(value,Dumper=transaction.vault_yaml.VaultDumper)))
            git(seed,'add','.')
            git(seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','Initialize fixture')
            git(seed,'remote','add','origin',str(remote));git(seed,'push','origin','main')
            (project/'myvars').write_bytes(vault.encrypt(yaml.safe_dump({'git_url':'https://git.example.invalid/fixture-owner/autodeploy.git'})))
            loader=DataLoader();loader.set_vault_secrets([('default',secret)])
            first_pushes = threading.Barrier(2)
            push_lock = threading.Lock()
            push_count = 0
            def redirected(command,*args,**kwargs):
                nonlocal push_count
                command=[str(remote) if value=='https://git.example.invalid/fixture-owner/aap_autodeploy_configascode-secrets.git' else value for value in command]
                self.assertFalse(any(value.startswith(('https://','http://','git@')) for value in command))
                self.assertNotIn('--force',command)
                if len(command) > 3 and command[3] == 'push':
                    with push_lock:
                        push_count += 1
                        initial = push_count <= 2
                    if initial:
                        first_pushes.wait(timeout=15)
                return real_run(command,*args,**kwargs)
            def invoke(phase,transition=None):
                plugin=module.ActionModule.__new__(module.ActionModule)
                args={'operation':'aap_supplemental_interface','phase':phase,'guest':guest,'hypervisor':pin}
                if transition is not None:args['transition']=transition
                plugin._task=SimpleNamespace(args=args,check_mode=False);plugin._loader=loader
                return plugin.run(task_vars={'awx_job_id':123,'awx_job_template_id':456,'awx_project_revision':'a'*40})
            with patch.object(ActionBase,'run',side_effect=lambda *args,**kwargs:{}),patch.object(module.ActionModule,'_project_root',return_value=project), \
                 patch.object(module,'SourceClient',return_value=source),patch.object(module.subprocess,'run',side_effect=redirected), \
                 patch.dict(os.environ,{'CAC_GIT_TOKEN':'synthetic-writer'}):
                plan=invoke('plan');self.assertNotIn('failed',plan,plan)
                self.assertFalse(plan['canonical_resource_present']);self.assertTrue(plan['canonical_resource_absent'])
                self.assertFalse(source.calls)
                request=source.request
                def interrupt(method,path,body=None):
                    if method=='PATCH':raise keys.StoreError('Synthetic interrupted source synchronization.')
                    return request(method,path,body)
                with patch.object(source,'request',side_effect=interrupt):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        failures = list(pool.map(lambda _: invoke('publish',plan['transition']),range(2)))
                self.assertTrue(all(result.get('failed') for result in failures),failures)
                self.assertTrue(any(result['durable_policy_published'] for result in failures),failures)
                fresh=invoke('plan');self.assertNotIn('failed',fresh,fresh)
                self.assertTrue(fresh['canonical_resource_present']);self.assertTrue(fresh['durable_ownership_published'])
                published=invoke('publish',fresh['transition']);self.assertTrue(published.get('published'),published)
                again=invoke('publish',fresh['transition']);self.assertFalse(again.get('changed'),again)
                self.assertEqual(git(remote,'rev-list','--count','main').stdout.strip(),'2')
                guest['primary']=fresh['transition']['desired_resource']
                guest['supplemental_state']='absent';guest['connection_readback']['connections']=[]
                remove=invoke('plan');self.assertNotIn('failed',remove,remove)
                self.assertTrue(remove['canonical_resource_present'])
                retired=invoke('publish',remove['transition']);self.assertTrue(retired.get('published'),retired)
                self.assertTrue(retired['canonical_resource_absent'])
                self.assertEqual(git(remote,'rev-list','--count','main').stdout.strip(),'3')
                restored={name:AnsibleLoader(vault.decrypt(git(remote,'show','main:'+name).stdout.encode())).get_single_data() for name in docs}
                self.assertEqual(restored,docs)
                self.assertTrue(all(method=='PATCH' and path.startswith('hosts/') for method,path in source.calls))


if __name__=='__main__': unittest.main()
