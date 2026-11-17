"""Project-scoped natural-language editorial review. No detector or fabricated language score.

Produces a transparent checklist and reusable editorial brief; human review remains essential.
"""
import re
try:
    from . import products, workspace
except ImportError:
    import products, workspace

LOCALES={'en-US':'US English','en-GB':'UK English','de-DE':'German (Germany)',
         'fr-FR':'French (France)','es-ES':'Spanish (Spain)','es-MX':'Spanish (Mexico)',
         'pt-BR':'Brazilian Portuguese','pt-PT':'European Portuguese','it-IT':'Italian (Italy)',
         'nl-NL':'Dutch (Netherlands)'}
CLICHES=(r'\bin today.s fast.paced world\b',r'\bleverage the power of\b',
         r'\bunlock your potential\b',r'\bgame.changer\b',r'\bseamless(ly)?\b',
         r'\bdelve into\b',r'\bcutting.edge\b',r'\blook no further\b',
         r'\brevolutioniz\w*\b',r'\btransformative journey\b')

def review(data):
    if not isinstance(data,dict):raise products.ProductError('Invalid editorial request')
    project=data.get('project')
    if project not in {p['id'] for p in products.custom_projects()}:raise products.ProductError('Unknown project')
    text=data.get('text');locale=data.get('locale','en-US');audience=data.get('audience','');tone=data.get('tone','natural')
    if not isinstance(text,str) or not 1<=len(text)<=12000:raise products.ProductError('Text must be 1–12,000 characters')
    if locale not in LOCALES:raise products.ProductError('Unsupported locale')
    if not isinstance(audience,str) or len(audience)>150 or not isinstance(tone,str) or len(tone)>60:
        raise products.ProductError('Invalid audience/tone')
    flags=[]
    for phrase in CLICHES:
        hits=re.findall(phrase,text,flags=re.I)
        if hits:flags.append({'type':'generic-phrase','detail':hits[0] if isinstance(hits[0],str) else 'Generic phrasing','count':len(hits)})
    if len(re.findall(r'!',text))>2:flags.append({'type':'excess-punctuation','detail':'Consider fewer exclamation marks'})
    sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',text) if x.strip()]
    if sentences and max(len(x.split()) for x in sentences)>36:
        flags.append({'type':'long-sentence','detail':'At least one sentence exceeds 36 words'})
    brief=(f'Edit for {LOCALES[locale]} and {audience.strip() or "the intended reader"}. '
           f'Use a {tone.strip() or "natural"} voice. Write idiomatically as a native speaker, not as a literal translation. Avoid templated AI phrasing, hype, repetition and filler. '
           'Preserve meaning, facts, quotations, terminology, brand voice and political neutrality. '
           'Prefer region-appropriate idioms and punctuation. Never invent evidence or translate legal claims without review. '
           'Explain substantive edits and flag ambiguity. A fluent native-language reviewer approves public copy.')
    return {'project':project,'locale':locale,'localeLabel':LOCALES[locale], 'flags':flags,
            'editorialBrief':brief,'readyToPublish':False,
            'message':'Automated lint completed. This is not a native-language review or verified fact check.'}


def start_editorial(data):
    """Run a natural-language editing request through the established Soni workflow.

    The provider remains customer-selected and existing model cost/consent rules apply.
    """
    try:
        from . import workspace
    except ImportError:
        import workspace
    result=review(data)
    task=(result['editorialBrief']+'\n\nRewrite this text while preserving its factual content. '
          'Return (1) edited text (2) brief substantive edit notes (3) open factual questions. '
          'Do not claim human editorial verification.\n\nSOURCE TEXT:\n'+data['text'])
    # Long passages exceed the standard 1,500-character Soni task limit: do not silently truncate.
    if len(task)>1500:
        raise products.ProductError('For Soni editing, text must fit the 1,500-character task limit. Local lint supports up to 12,000.')
    response=workspace.start_run(data['project'],{'task':task,'provider':data.get('provider','mock'),'consent':data.get('consent') is True})
    return {'run':response,'editorial':result}
