"""Reproducible optional challenge scenarios and explicit pair judgements.

These hand-authored fictional scenarios are controlled fixtures, not human-reviewed
benchmark data. Canonical synthetic-v1 files are never replaced.
"""
import hashlib
import json
from pathlib import Path
import random
from .dataset import generate, SEED, write_generated_files
from .paths import resource_path
from .ingestion import export_jsonl
from .signals import analyze_report

# Each tuple is one fictional event with three independently phrased language views.
SCENARIOS = [
    ('theft','Lotus','2025-03-01T09:00:00+06:00',
     'A camera labelled CAM-410 vanished during the Lotus library exhibition. Person: Arif Noor; a red van left the west entrance.',
     'পদ্ম গ্রন্থাগারের প্রদর্শনী থেকে CAM-410 লেখা ক্যামেরা চুরি হয়েছে। ব্যক্তি: আরিফ নূর; পশ্চিম ফটক দিয়ে লাল ভ্যান চলে যায়।',
     'Lotus library exhibition e CAM-410 camera missing. Red van west gate diye geche; Person: Arif Noor.'),
    ('fire','River','2025-03-04T21:30:00+06:00',
     'A small fire damaged the River theatre costume room. A witness noticed smoke after a lamp fell. Organization: River Theatre.',
     'নদী থিয়েটারের পোশাক ঘরে বাতি পড়ে আগুন লাগে। ধোঁয়া দেখে একজন সাক্ষী খবর দেন। সংস্থা: নদী থিয়েটার।',
     'River theatre costume room e lamp pore smoke and fire hoy. Organization: River Theatre.'),
    ('damage','Cedar','2025-03-06T07:00:00+06:00',
     'The glass door of Cedar workshop was broken overnight. Blue paint was visible on a trolley beside the doorway. Identifier: DOOR-62.',
     'দেবদারু কর্মশালার কাচের দরজা রাতে ভাঙা হয়। দরজার পাশে ঠেলাগাড়িতে নীল রং ছিল। আইডি: DOOR-62।',
     'Cedar workshop er glass door broken overnight. Door er pashe blue trolley, Identifier: DOOR-62.'),
    ('lost_property','Moon','2025-03-09T15:00:00+06:00',
     'A wallet was found under a seat at Moon auditorium after a music rehearsal. Identifier: WAL-88. No theft was alleged.',
     'চাঁদ মিলনায়তনে মহড়ার পরে আসনের নিচে মানিব্যাগ পাওয়া গেছে। আইডি: WAL-88। চুরির অভিযোগ নেই।',
     'Moon auditorium rehearsal er pore seat er niche wallet found. Identifier: WAL-88. No complaint of theft.'),
    ('missing_property','Garden',None,
     'A parcel intended for Garden art club did not arrive. The sender recalls a green seal but no delivery time. Organization: Garden Art Club.',
     'বাগান শিল্প ক্লাবের পার্সেল পৌঁছায়নি। প্রেরক সবুজ সিলের কথা বলেছেন, সময় জানা নেই। সংস্থা: বাগান শিল্প ক্লাব।',
     'Garden Art Club er parcel delivery hoyni. Green seal chilo; exact time unknown. Organization: Garden Art Club.'),
    ('damage','Hill','2025-03-12T12:30:00+06:00',
     'A water pipe burst inside Hill science hall. A laptop marked LAB-703 was damaged. Maintenance reported pressure loss before noon.',
     'পাহাড় বিজ্ঞান ভবনের পানির পাইপ ফেটে LAB-703 লেখা ল্যাপটপ নষ্ট হয়। দুপুরের আগে পানির চাপ কমে যায়।',
     'Hill science hall e pipe burst, laptop LAB-703 damaged. Noon er age water pressure low chilo.'),
    ('theft','River','2025-03-13T18:00:00+06:00',
     'A bicycle with a striped basket disappeared outside River swimming pool. It was not the parcel delivery bicycle. Identifier: CYCLE-19.',
     'নদী সাঁতার কেন্দ্রের সামনে থেকে ডোরাকাটা ঝুড়ির সাইকেল চুরি হয়। এটি পার্সেল বহনের সাইকেল নয়। আইডি: CYCLE-19।',
     'River pool er striped basket bicycle missing, delivery bicycle na. Identifier: CYCLE-19.'),
    ('fire','Lotus','2025-03-16T20:00:00+06:00',
     'Smoke entered Lotus cafe from a scorched toaster. No property disappeared and nobody reported a van. Organization: Lotus Cafe.',
     'পদ্ম ক্যাফেতে টোস্টার পুড়ে ধোঁয়া হয়। কিছু হারায়নি, ভ্যানের কথাও কেউ বলেননি। সংস্থা: পদ্ম ক্যাফে।',
     'Lotus cafe te toaster burn kore smoke. Kichu missing na; no van observed. Organization: Lotus Cafe.'),
    ('damage',None,None,
     'An unmarked storage window was broken. The reporter cannot recall the site or date. A camera captured only a shadow.',
     'একটি অচিহ্নিত গুদামের জানালা ভাঙা হয়েছে। স্থান ও তারিখ মনে নেই। ক্যামেরায় শুধু ছায়া দেখা যায়।',
     'Storage window broken, exact place and date unknown. Camera te only shadow visible.'),
    ('lost_property','Cedar','2025-03-19T08:00:00+06:00',
     'A silver lantern was returned to Cedar museum by a visitor who found it on a bench. Person: Samira Rahman; Identifier: LANT-05.',
     'দেবদারু জাদুঘরের বেঞ্চে পাওয়া রুপালি লণ্ঠন দর্শনার্থী ফেরত দেন। ব্যক্তি: সামিরা রহমান; আইডি: LANT-05।',
     'Cedar museum bench e silver lantern found and returned. Person: Samira Rahman; Identifier: LANT-05.'),
    ('missing_property','Hill','2025-03-22T16:00:00+06:00',
     'A parcel of theatre tickets went missing near Hill bus stop. A witness mentioned a blue cart but could not identify its owner. Identifier: BOX-92.',
     'পাহাড় বাসস্টপের কাছে থিয়েটারের টিকিটের পার্সেল হারায়। সাক্ষী নীল ঠেলাগাড়ি দেখেন কিন্তু মালিক চিনতে পারেননি। আইডি: BOX-92।',
     'Hill bus stop e tickets parcel missing. Blue cart dekha geche, owner unknown. Identifier: BOX-92.'),
    ('damage','Garden','2025-03-25T10:00:00+06:00',
     'A red van struck the Garden community hall sign during a rehearsal delivery. The driver stopped and left a note. Registration: DEMO-301.',
     'মহড়ার জিনিস আনতে গিয়ে লাল ভ্যান বাগান কমিউনিটি হলের সাইনবোর্ডে ধাক্কা দেয়। চালক থেমে চিরকুট রাখেন। নিবন্ধন: DEMO-301।',
     'Garden community hall sign e red van hit kore. Driver stopped and note rekhe geche. Registration: DEMO-301.'),
]
SINGLETONS = [
    ('en','A fictional weather observer recorded hail at an isolated lighthouse. No other report describes this event.'),
    ('bn','কাল্পনিক পাহাড়ি আবহাওয়া কেন্দ্রে বিরল তুষারপাত নথিভুক্ত হয়েছে। এই ঘটনার আর কোনো প্রতিবেদন নেই।'),
    ('mixed','Fictional astronomy club e meteor observation record hoyeche. This event has no companion report.'),
]


def generate_challenge(seed=SEED):
    order = list(range(len(SCENARIOS)))
    random.Random(seed).shuffle(order)
    splits = {family:'train' if i<6 else 'dev' if i<9 else 'test' for i,family in enumerate(order)}
    result = []
    for i,(kind,location,date,*texts) in enumerate(SCENARIOS):
        for j,(language,text) in enumerate(zip(['en','bn','mixed'],texts)):
            rid=f'X{i:02d}-{j}'
            metadata=dict(family_id=f'XF{i:02d}',split=splits[i],language=language,
                          variant='challenge_incomplete' if location is None or date is None else 'challenge_paraphrase',
                          generator_version='challenge-v1',source_id=f'synthetic:challenge-v1:{rid}',
                          incident_type=kind,location=location,occurred_at=date,
                          annotation_status='controlled author assignment; not independently reviewed')
            result.append(analyze_report(text,rid,metadata))
    for i,(language,text) in enumerate(SINGLETONS):
        rid=f'XN{i:02d}'
        result.append(analyze_report(text,rid,dict(family_id=f'XNF{i:02d}',split=['train','dev','test'][i],language=language,
                                                  variant='no_match',generator_version='challenge-v1',source_id=f'synthetic:challenge-v1:{rid}')))
    return result


def qrels(records):
    """Explicit binary family judgements for all within-partition ordered pairs."""
    return [dict(query_id=a['report_id'],candidate_id=b['report_id'],split=a['split'],
                 grade=int(a['family_id']==b['family_id']),
                 rationale='Same constructed scenario family' if a['family_id']==b['family_id'] else 'Different constructed scenario family',
                 annotator='synthetic-generator',version='family-qrels-v1')
            for a in records for b in records if a['report_id']!=b['report_id'] and a['split']==b['split']]


def write_challenge(root=None, overwrite=False):
    root = Path(root) if root is not None else resource_path('dataset')
    root.mkdir(parents=True,exist_ok=True)
    records=generate_challenge()
    payload=export_jsonl(records).encode('utf-8')
    manifest=dict(seed=SEED,version='challenge-v1',count=len(records),sha256=hashlib.sha256(payload).hexdigest(),
                  family_splits={r['family_id']:r['split'] for r in records},
                  source='original authored fictional scenarios; not independently reviewed')
    write_generated_files({root / 'challenge_reports.jsonl': payload,
                           root / 'challenge_manifest.json': json.dumps(manifest, indent=2).encode('utf-8'),
                           root / 'challenge_qrels.jsonl': export_jsonl(qrels(records)).encode('utf-8'),
                           root / 'qrels.jsonl': export_jsonl(qrels(generate())).encode('utf-8')}, overwrite=overwrite)
    return manifest


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    print(json.dumps(write_challenge(args.directory, overwrite=args.overwrite), indent=2))
