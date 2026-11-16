"""Behavioral design acceptance checks; SVG semantics do not prove visual quality."""
from copy import deepcopy
import re
import unittest
import xml.etree.ElementTree as ET
from streamlit.testing.v1 import AppTest
from sherlocked.design import ROOT,TOKENS,THEMES,signal_chart


def contrast(foreground,background):
    def luminance(color):
        rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb]
        return sum(a*b for a,b in zip(linear,[.2126,.7152,.0722]))
    light,dark=sorted([luminance(foreground),luminance(background)],reverse=True)
    return (light+.05)/(dark+.05)


class NoirDesignTests(unittest.TestCase):
    def test_source_quote_preserves_unicode_and_escapes_markup_before_highlighting(self):
        text='Source <img src=x onerror=alert(1)> পদ্ম & সাইকেল।'
        reference='source:<script>unsafe</script>'
        image_start=text.index('<img');image_end=text.index('>')+1
        bn_start=text.index('পদ্ম');bn_end=bn_start+len('পদ্ম')
        spans=[(bn_start,bn_end),(image_start,image_end),(-1,4),(0,len(text)+1),(7,3),('0',5),(None,3)]
        script='from sherlocked.design import source_quote\nsource_quote('+ascii(text)+','+ascii(reference)+','+ascii(spans)+')'
        app=AppTest.from_string(script,default_timeout=20).run()
        self.assertFalse(app.exception,str(app.exception))
        markup=next(item.value for item in app.markdown if 'sk-source-quote' in item.value)
        tree=ET.fromstring('<root>'+markup+'</root>')
        quote=tree.find("div[@class='sk-source-quote']")
        self.assertEqual(''.join(quote.itertext()),text)
        self.assertEqual([node.text for node in quote.findall('mark')],[text[image_start:image_end],'পদ্ম'])
        self.assertEqual(''.join(tree.find("div[@class='sk-source-ref']").itertext()),reference)
        self.assertIsNone(tree.find('.//img'))
        self.assertIsNone(tree.find('.//script'))

    def test_signal_chart_keeps_raw_values_and_does_not_invent_missing_signals(self):
        hit={'components':{'tfidf':.4,'bm25':17.2,'semantic':None,'entity':0.,'structured':None},
             'normalized_components':{'tfidf':.4,'bm25':.8,'semantic':.99,'entity':0.,'structured':1.}}
        original=deepcopy(hit)
        figure=signal_chart(hit);bars=figure.data[0]
        self.assertEqual(list(bars.x),[.4,.8,0.])
        self.assertEqual(list(bars.customdata),[.4,17.2,0.])
        self.assertEqual(len(bars.y),3)
        self.assertNotIn('Multilingual semantic',bars.y)
        self.assertNotIn('Structured context',bars.y)
        self.assertEqual([float(value) for value in bars.text],[.4,17.2,0.])
        self.assertEqual(hit,original)
        self.assertIn('not probability',figure.layout.xaxis.title.text.casefold())

    def test_primary_normal_text_pairs_meet_wcag_aa(self):
        # Main body/captions, dark navigation, review labels and error/button text.
        # Border-only and decorative accents are not evaluated as body text.
        pairs=[('ink','paper'),('muted','paper'),('ink','paper-card'),('muted','paper-card'),
               ('ivory','ink'),('ivory','ink-card'),('rose','ink-card'),('brass','ink'),
               ('oxblood','paper-card'),('paper-card','oxblood')]
        for foreground,background in pairs:
            with self.subTest(foreground=foreground,background=background):
                self.assertGreaterEqual(contrast(TOKENS[foreground],TOKENS[background]),4.5)

    def test_both_semantic_theme_text_surfaces_meet_wcag_aa(self):
        for mode,colors in THEMES.items():
            for role in ['text','muted','accent']:
                for surface in ['bg','surface','raised']:
                    with self.subTest(mode=mode,role=role,surface=surface):
                        self.assertGreaterEqual(contrast(colors[role],colors[surface]),4.5)

    def test_logo_variants_are_self_contained_svg_with_required_semantic_paths(self):
        paths=sorted((ROOT/'assets/branding').glob('*.svg'))
        self.assertGreaterEqual(len(paths),6)
        for path in paths:
            with self.subTest(asset=path.name):
                payload=path.read_text(encoding='utf-8-sig')
                self.assertNotIn('<!DOCTYPE',payload.upper())
                self.assertNotIn('<!ENTITY',payload.upper())
                tree=ET.fromstring(payload)
                self.assertEqual(tree.tag,'{http://www.w3.org/2000/svg}svg')
                ids={node.get('id'):node for node in tree.iter() if node.get('id')}
                # Semantic asset contract only. A human must inspect hat/profile/pipe appearance.
                for required in ['deerstalker','profile','curved-pipe']:
                    self.assertIn(required,ids)
                    self.assertTrue(ids[required].get('d','').strip())
                for node in tree.iter():
                    tag=node.tag.rsplit('}',1)[-1].casefold()
                    self.assertNotIn(tag,{'script','foreignobject','image'})
                    for name,value in node.attrib.items():
                        if name.rsplit('}',1)[-1].casefold()=='href':
                            self.assertTrue(value.startswith('#'),'External SVG resource')
                        for reference in re.findall(r'url\(([^)]+)\)',value):
                            self.assertTrue(reference.strip(' \'\"').startswith('#'),'External SVG paint resource')
                    if tag=='style':
                        self.assertNotIn('@import',node.text or '')
                        self.assertFalse(re.search(r'url\(\s*[\'\"]?(?:https?:|//)',node.text or '',re.I))
        favicon=ET.parse(ROOT/'assets/branding/favicon.svg').getroot()
        viewbox=[float(number) for number in favicon.get('viewBox','').split()]
        self.assertEqual(len(viewbox),4)
        self.assertGreater(viewbox[2],0)
        self.assertEqual(viewbox[2],viewbox[3])


if __name__=='__main__': unittest.main()
