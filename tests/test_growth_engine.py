"""Functional acceptance of CariFive Growth OS on real persistent local ledgers."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import products, growth_engine as g


def profile():
    return {'product':'Booking tool','audience':'Small venue owners',
            'buyer':'Independent operators','offer':'Reduce missed bookings',
            'conversion':'Demo request','positioning':'Simple self-service booking',
            'successMetric':'Qualified demo requests','successThreshold':'10',
            'channels':{'linkedin':'EXISTS_AND_USABLE'},
            'assets':['existing product screenshot'],
            'evidence':['Owner-reviewed product brief'],
            'reviewedByOwner':True}


def opportunity_scores(**changes):
    values={'brandFit':9,'originality':9,'timing':9,'expectedAttention':9,
            'shareability':9,'conversionPotential':9,'earnedMediaPotential':7,
            'effort':2,'reputationalRisk':1,'legalIpRisk':1,'misinterpretationRisk':1}
    values.update(changes)
    return values


def creative_scores(**changes):
    values={'originality':9.2,'hook':9,'conversion':9,'shareability':9,
            'naturalness':9.5,'audienceRelevance':9.5,'brandFit':9.5}
    values.update(changes)
    return values


class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.old=products.STATE
        products.STATE=Path(self.tmp.name)
        self.pid='standard-slot-1'

    def tearDown(self):
        products.STATE=self.old
        self.tmp.cleanup()

    def ready(self):
        return g.brand_profile(self.pid,profile())

    def mischief(self):
        return g.set_mischief(self.pid,{'voice':'Sharp, helpful, understated',
            'humor':7,'provocation':3,'prohibitedThemes':['fake testimonial'],
            'boundaries':'No sensitive claims or fabricated reviews'})

    def opportunity(self,**changes):
        return g.add_opportunity(self.pid,{'title':'Industry event','source':'Owner-reviewed event page',
            'reason':'Relevant venue owners attending','scores':opportunity_scores(**changes)})

    def experiment(self,opp=None):
        opp=opp or self.opportunity()
        return g.create_experiment(self.pid,{'opportunityId':opp['id'],
            'channel':'linkedin','hypothesis':'Relevant operator outreach earns demos',
            'primaryMetric':'Qualified demos','threshold':10,'assetRoute':'existing product screenshot',
            'cta':'Book a demo'})

    def test_unreviewed_brand_fails_readiness(self):
        body=profile();body['reviewedByOwner']=False
        self.assertEqual(g.brand_profile(self.pid,body)['readiness']['status'],'FAIL')

    def test_missing_asset_or_evidence_does_not_pass(self):
        body=profile();body['assets']=[];body['evidence']=[]
        result=g.brand_profile(self.pid,body)['readiness']
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('assets',result['missing'])
        self.assertIn('evidence',result['missing'])

    def test_blocked_unknown_channel_causes_blocked_status(self):
        body=profile();body['channels']['reddit']='BLOCKED_UNKNOWN'
        self.assertEqual(g.brand_profile(self.pid,body)['readiness']['status'],'BLOCKED')

    def test_complete_owner_reviewed_brand_passes(self):
        self.assertEqual(self.ready()['readiness']['status'],'PASS')
        self.assertEqual(g.overview(self.pid)['channels']['linkedin'],'EXISTS_AND_USABLE')

    def test_bad_platform_classification_rejected(self):
        body=profile();body['channels']={'linkedin':'CONNECTED_AND_VERIFIED'}
        with self.assertRaises(products.ProductError):g.brand_profile(self.pid,body)

    def test_brand_ledgers_isolated(self):
        self.ready()
        self.assertIsNone(g.overview('standard-slot-2')['brand'])
        self.assertEqual(g.overview('standard-slot-2')['readiness']['status'],'FAIL')
        self.assertNotEqual(g.overview('standard-slot-2')['project'],self.pid)

    def test_mischief_profile_persists(self):
        self.mischief()
        self.assertEqual(g.overview(self.pid)['mischief']['voice'],'Sharp, helpful, understated')

    def test_weak_creative_rejected_even_with_high_average(self):
        self.mischief()
        q=g.review_creative(self.pid,{'content':'Watch our booking demo','channel':'linkedin',
            'scores':creative_scores(naturalness=9.4),'factChecked':True,'rulesChecked':True})
        self.assertFalse(q['passed'])
        self.assertIn('naturalness',q['issues'])
        self.assertFalse(q['published'])

    def test_creative_passing_threshold_and_factual_checks(self):
        self.mischief()
        q=g.review_creative(self.pid,{'content':'Booking workflow demo','channel':'linkedin',
            'scores':creative_scores(),'factChecked':True,'rulesChecked':True})
        self.assertTrue(q['passed'])
        self.assertTrue(q['estimatedQualityOnly'])

    def test_creative_banned_theme_rejected(self):
        self.mischief()
        q=g.review_creative(self.pid,{'content':'Our fake testimonial promises success',
            'channel':'linkedin','scores':creative_scores(),
            'factChecked':True,'rulesChecked':True})
        self.assertFalse(q['passed'])
        self.assertIn('prohibited brand theme',q['issues'])

    def test_unreviewed_legal_claim_rejected(self):
        self.mischief()
        q=g.review_creative(self.pid,{'content':'Claims about law','channel':'linkedin',
            'scores':creative_scores(),'factChecked':False,'rulesChecked':True})
        self.assertFalse(q['passed'])

    def test_reactive_radar_handles_high_risk(self):
        op=self.opportunity(legalIpRisk=9)
        self.assertEqual(op['decision'],'ESCALATE')
        self.assertTrue(op['hypothesis'])

    def test_reactive_radar_rejects_weak_fit(self):
        op=self.opportunity(brandFit=1,originality=1,timing=1,expectedAttention=1,
                            shareability=1,conversionPotential=1,earnedMediaPotential=1,
                            effort=10,reputationalRisk=7,legalIpRisk=7,misinterpretationRisk=7)
        self.assertEqual(op['decision'],'IGNORE')

    def test_radar_requirements_fail_closed(self):
        with self.assertRaises(products.ProductError):
            g.add_opportunity(self.pid,{'title':'Trend','source':'Note',
                'reason':'Guess','scores':{'brandFit':10}})

    def test_today_selects_one_best_action_and_no_fake_execution(self):
        self.ready()
        first=self.opportunity(conversionPotential=6)
        second=self.opportunity(conversionPotential=10)
        outcome=g.today()
        self.assertEqual(outcome['status'],'SUPPORTED')
        self.assertEqual(outcome['action']['opportunityId'],second['id'])
        self.assertEqual(outcome['action']['execution'],'not-started')
        self.experiment(second)
        self.assertEqual(g.today()['action']['opportunityId'],first['id'])

    def test_today_returns_no_evidence_when_brand_not_ready(self):
        self.opportunity()
        self.assertEqual(g.today()['status'],'NEEDS_MORE_EVIDENCE')

    def test_experiment_rejects_foreign_brand_opportunity(self):
        opportunity=self.opportunity()
        with self.assertRaises(products.ProductError):
            g.create_experiment('standard-slot-2',{'opportunityId':opportunity['id'],
                'channel':'linkedin','hypothesis':'Test','primaryMetric':'Leads',
                'threshold':10,'assetRoute':'existing','cta':'Visit'})

    def test_experiment_persistent_lifecycle_and_measurement(self):
        self.ready()
        e=self.experiment()
        self.assertEqual(e['status'],'DRAFT')
        with self.assertRaises(products.ProductError):
            g.transition(self.pid,e['id'],{'status':'APPROVED','ownerApproved':True})
        with self.assertRaises(products.ProductError):
            g.transition(self.pid,e['id'],{'status':'READY_FOR_APPROVAL'})
        self.mischief()
        review=g.review_creative(self.pid,{'content':'Professional booking demo',
            'channel':'linkedin','scores':creative_scores(),'factChecked':True,'rulesChecked':True})
        g.transition(self.pid,e['id'],{'status':'READY_FOR_APPROVAL',
            'creativeReviewId':review['id']})
        with self.assertRaises(products.ProductError):
            g.transition(self.pid,e['id'],{'status':'APPROVED'})
        g.transition(self.pid,e['id'],{'status':'APPROVED','ownerApproved':True})
        with self.assertRaises(products.ProductError):
            g.transition(self.pid,e['id'],{'status':'RUNNING','executionEvidence':'manual'})
        with self.assertRaises(products.ProductError):
            g.transition(self.pid,e['id'],{'status':'RUNNING'})
        g.transition(self.pid,e['id'],{'status':'RUNNING',
            'manualLaunchEvidence':'Founder reports sending one compliant personal message'})
        m=g.measure(self.pid,e['id'],{'value':11,'source':'Manually reviewed CRM',
           'observedAt':'2026-11-26T13:00:00+01:00'})
        self.assertEqual(m['experiment']['outcome'],'SCALE')
        self.assertTrue(m['experiment']['outcomeIsProvisional'])
        self.assertFalse(m['experiment']['measurements'][0]['verified'])
        self.assertFalse(m['experiment']['externalActionExecuted'])
        self.assertEqual(g.overview(self.pid)['experiments'][0]['status'],'MEASURED')

    def test_unready_brand_cannot_submit_experiment_for_approval(self):
        self.mischief()
        e=self.experiment()
        review=g.review_creative(self.pid,{'content':'Relevant venue booking demo',
            'channel':'linkedin','scores':creative_scores(),
            'factChecked':True,'rulesChecked':True})
        with self.assertRaisesRegex(products.ProductError,'Brand readiness'):
            g.transition(self.pid,e['id'],{'status':'READY_FOR_APPROVAL',
                'creativeReviewId':review['id']})

    def test_high_risk_opportunity_cannot_enter_routine_approval(self):
        self.ready()
        self.mischief()
        e=self.experiment(self.opportunity(legalIpRisk=9))
        review=g.review_creative(self.pid,{'content':'Ethical event idea',
            'channel':'linkedin','scores':creative_scores(),
            'factChecked':True,'rulesChecked':True})
        with self.assertRaisesRegex(products.ProductError,'Risk'):
            g.transition(self.pid,e['id'],{'status':'READY_FOR_APPROVAL',
                'creativeReviewId':review['id']})

    def test_fake_creative_review_id_cannot_unlock_campaign(self):
        self.ready()
        self.mischief()
        e=self.experiment()
        with self.assertRaisesRegex(products.ProductError,'Passing saved creative review'):
            g.transition(self.pid,e['id'],{'status':'READY_FOR_APPROVAL',
                'creativeReviewId':'CRE-FORGED'})

    def test_measurement_cannot_precede_run(self):
        e=self.experiment()
        with self.assertRaises(products.ProductError):
            g.measure(self.pid,e['id'],{'value':9,'source':'CRM','observedAt':'2026-11-26T00:00:00Z'})

    def test_website_intervention_requires_evidence_flag(self):
        self.ready()
        e=self.experiment()
        self.mischief()
        review=g.review_creative(self.pid,{'content':'Professional booking demo',
            'channel':'linkedin','scores':creative_scores(),'factChecked':True,'rulesChecked':True})
        g.transition(self.pid,e['id'],{'status':'READY_FOR_APPROVAL',
            'creativeReviewId':review['id']})
        g.transition(self.pid,e['id'],{'status':'APPROVED','ownerApproved':True})
        g.transition(self.pid,e['id'],{'status':'RUNNING',
            'manualLaunchEvidence':'Founder reports sending one compliant personal message'})
        m=g.measure(self.pid,e['id'],{'value':2,'source':'Landing analytics',
            'observedAt':'2026-11-26T00:00:00Z','websiteEvidence':True})
        self.assertEqual(m['experiment']['outcome'],'WEBSITE_INTERVENTION_REQUIRED')

    def test_default_autonomy_and_l3_requires_owner_approval(self):
        self.assertEqual(g.overview(self.pid)['autonomy']['level'],2)
        with self.assertRaises(products.ProductError):
            g.set_autonomy(self.pid,{'level':4,'authorizedChannels':['reddit'],
                'authorizedLowRiskTypes':['routine-post'],'scopeApproved':False})
        scope=g.set_autonomy(self.pid,{'level':3,'authorizedChannels':['linkedin'],
            'authorizedLowRiskTypes':['routine-post'],'scopeApproved':True})
        self.assertEqual(scope['level'],3)
        self.assertTrue(g.requires_specific_approval('paid-spend'))
        self.assertTrue(g.requires_specific_approval('political-content'))
        self.assertTrue(g.requires_specific_approval('physical-activation'))

    def test_dashboard_does_not_invent_commercial_outcomes(self):
        self.ready()
        report=g.dashboard()
        self.assertEqual(report['count'],1)
        self.assertIsNone(report['verifiedCommercialOutcomes'])
        self.assertEqual(report['brands'][0]['readiness'],'PASS')

    def test_unknown_project_denied(self):
        with self.assertRaises(products.ProductError):g.overview('../other')
        with self.assertRaises(products.ProductError):g.set_mischief('../other',{})


if __name__=='__main__':
    unittest.main()
