import json
import threading
import unittest
from http.server import HTTPServer
from unittest.mock import patch
import requests
import authorize_drive as app

class Reply:
    status_code = 200
    def __init__(self, data): self.data = data
    def json(self): return self.data

class FolderTests(unittest.TestCase):
    def test_folder_requires_write(self):
        for data in [dict(id=app.TARGET,name='Tictoc',mimeType='application/pdf',capabilities={'canAddChildren':True}),dict(id=app.TARGET,name='Tictoc',mimeType='application/vnd.google-apps.folder',capabilities={'canAddChildren':False})]:
            with self.assertRaises(ValueError): app.check_folder('fixture',app.TARGET,get=lambda *a,**k:Reply(data))
    def test_valid_folder(self):
        def get(*a,**k):
            self.assertEqual(k['headers']['Authorization'],'Bearer fixture')
            self.assertEqual(k['timeout'],(10,45))
            return Reply(dict(id=app.TARGET,name='Tictoc',mimeType='application/vnd.google-apps.folder',capabilities={'canAddChildren':True}))
        self.assertEqual(app.check_folder('fixture',app.TARGET,get)['name'],'Tictoc')
    def test_invalid_id_not_requested(self):
        with self.assertRaises(ValueError): app.check_folder('fixture','../../token')

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.result={};self.server=HTTPServer(('127.0.0.1',0),app.make_handler('fixture','fake-key','123','testnonce',self.result));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_port);self.session=requests.Session();self.session.trust_env=False
    def tearDown(self): self.server.shutdown();self.server.server_close();self.thread.join();self.session.close()
    def test_token_route_host_and_capability(self):
        self.assertEqual(self.session.get(self.url+'/wrong/config').status_code,404)
        self.assertEqual(self.session.get(self.url+'/testnonce/config',headers={'Host':'attacker.invalid'}).status_code,403)
        r=self.session.get(self.url+'/testnonce/config');self.assertEqual(r.json()['token'],'fixture');self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertNotIn('Access-Control-Allow-Origin',r.headers)
    def test_cross_origin_cannot_select(self):
        r=self.session.post(self.url+'/testnonce/selection',headers={'Origin':'https://attacker.invalid'},json={'id':app.TARGET});self.assertEqual(r.status_code,403);self.assertFalse(self.result)
    def test_selection_verified(self):
        with patch.object(app,'check_folder',return_value={'id':app.TARGET,'name':'Tictoc'}) as check:
            r=self.session.post(self.url+'/testnonce/selection',headers={'Origin':self.url},json={'id':app.TARGET});self.assertEqual(r.status_code,200);check.assert_called_once_with('fixture',app.TARGET);self.assertEqual(self.result['folder']['name'],'Tictoc')
    def test_other_folder_rejected_before_api(self):
        with patch.object(app,'check_folder') as check:
            r=self.session.post(self.url+'/testnonce/selection',headers={'Origin':self.url},json={'id':'other_folder_123'});self.assertEqual(r.status_code,400);check.assert_not_called();self.assertFalse(self.result)

if __name__=='__main__': unittest.main()
