"""Loopback integration tests: Growth OS must work through the actual HTTP controller."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import control_server, products


class GrowthApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.previous=products.STATE
        products.STATE=Path(self.tmp.name)
        self.server=control_server.create_local_server(0)
        self.port=self.server.server_port
        self.base=f'http://127.0.0.1:{self.port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        products.STATE=self.previous
        self.tmp.cleanup()

    def call(self,path,data=None):
        headers={'Origin':self.base}
        if data is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request(self.base+path,
            data=json.dumps(data).encode() if data is not None else None,
            headers=headers,method='POST' if data is not None else 'GET')
        try:
            with urllib.request.urlopen(req,timeout=5) as response:
                return response.status,json.loads(response.read())
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read())

    def test_full_safe_lifecycle_through_http(self):
        pid='standard-slot-1'
        brand={'product':'Venue booking','audience':'Venues','buyer':'Independent operators',
            'offer':'Simple online bookings','conversion':'Qualified demo',
            'positioning':'Straightforward bookings','successMetric':'Demos',
            'successThreshold':'8','channels':{'linkedin':'EXISTS_AND_USABLE'},
            'assets':['Screenshot'],'evidence':['Reviewed local product specification'],
            'reviewedByOwner':True}
        code,answer=self.call('/api/growth/brand/'+pid,brand)
        self.assertEqual(code,200,answer)
        self.assertEqual(answer['readiness']['status'],'PASS')
        code,answer=self.call('/api/growth/mischief/'+pid,
            {'voice':'Witty but factual','humor':6,'provocation':2,
             'prohibitedThemes':['fabricated review'],
             'boundaries':'No invented customer results'})
        self.assertEqual(code,200,answer)
        scores={'brandFit':9,'originality':9,'timing':9,'expectedAttention':9,
                'shareability':9,'conversionPotential':9,'earnedMediaPotential':8,
                'effort':2,'reputationalRisk':1,'legalIpRisk':1,'misinterpretationRisk':1}
        code,opp=self.call('/api/growth/opportunity/'+pid,
            {'title':'Operator meet-up','reason':'Exact audience','source':'Event listing',
             'scores':scores})
        self.assertEqual(code,200,opp)
        self.assertEqual(opp['decision'],'CREATE GROWTH TEST')
        code,today=self.call('/api/growth/today')
        self.assertEqual(today['action']['project'],pid)
        quality={'originality':9,'hook':9,'conversion':9,'shareability':9,
            'naturalness':9.5,'audienceRelevance':9.5,'brandFit':9.5}
        code,review=self.call('/api/growth/creative-review/'+pid,
            {'content':'See a booking workflow demo','channel':'linkedin',
             'scores':quality,'factChecked':True,'rulesChecked':True})
        self.assertEqual(code,200,review)
        self.assertTrue(review['passed'])
        code,ex=self.call('/api/growth/experiment/'+pid,
            {'opportunityId':opp['id'],'channel':'linkedin',
             'hypothesis':'A demo invites venue owner responses','primaryMetric':'Qualified demos',
             'threshold':8,'assetRoute':'Existing screenshot','cta':'Book a demo'})
        self.assertEqual(code,200,ex)
        self.assertEqual(ex['status'],'DRAFT')
        route='/api/growth/transition/'+pid+'/'+ex['id']
        code,error=self.call(route,{'status':'APPROVED','ownerApproved':True})
        self.assertEqual(code,400,error)
        code,stage=self.call(route,{'status':'READY_FOR_APPROVAL',
                                   'creativeReviewId':review['id']})
        self.assertEqual(code,200,stage)
        code,error=self.call(route,{'status':'APPROVED'})
        self.assertEqual(code,400,error)
        code,approved=self.call(route,{'status':'APPROVED','ownerApproved':True})
        self.assertEqual(code,200,approved)
        code,error=self.call(route,{'status':'RUNNING'})
        self.assertEqual(code,400,error)
        code,running=self.call(route,{'status':'RUNNING',
            'manualLaunchEvidence':'Owner separately sent one personalized message'})
        self.assertEqual(code,200,running)
        self.assertEqual(running['launchVerification'],'manual-unverified')
        self.assertFalse(running['externalActionExecuted'])
        code,measured=self.call('/api/growth/measure/'+pid+'/'+ex['id'],
            {'value':8,'source':'Owner-entered CRM notes',
             'observedAt':'2026-11-26T12:00:00Z'})
        self.assertEqual(code,200,measured)
        self.assertEqual(measured['experiment']['outcome'],'SCALE')
        self.assertTrue(measured['experiment']['outcomeIsProvisional'])
        code,view=self.call('/api/growth/project/'+pid)
        self.assertEqual(view['experiments'][0]['status'],'MEASURED')
        self.assertEqual(len(view['creativeReviews']),1)
        code,dash=self.call('/api/growth/dashboard')
        self.assertEqual(dash['count'],1)
        self.assertIsNone(dash['verifiedCommercialOutcomes'])

    def test_reject_unknown_cross_project_and_invalid_payload(self):
        status,error=self.call('/api/growth/project/not-a-project')
        self.assertEqual(status,400,error)
        status,error=self.call('/api/growth/brand/standard-slot-1',{})
        self.assertEqual(status,400,error)
        status,error=self.call('/api/growth/opportunity/standard-slot-2',
            {'title':'Trend','source':'No source','reason':'No proof','scores':{}})
        self.assertEqual(status,400,error)


if __name__=='__main__':
    unittest.main()
