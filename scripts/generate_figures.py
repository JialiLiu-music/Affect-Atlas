"""Reproduce paper figures from immutable local experiment JSON, without inference.
Run: python lunwen2/scripts/generate_figures.py --workspace . --output lunwen2/figures
Only output files are written. PDF/SVG are native vectors; PNG is 300 dpi.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    ws = args.workspace.resolve()
    allowed = ws / 'lunwen2' / 'figures'
    out = (args.output or allowed).resolve()
    if not out.is_relative_to(allowed.resolve()):
        parser.error('--output must be inside WORKSPACE/lunwen2/figures')
    out.mkdir(parents=True, exist_ok=True)
    sys.dont_write_bytecode = True
    os.environ['MPLCONFIGDIR'] = str(out / '_mplconfig')
    local_deps = allowed / '_deps'
    if local_deps.exists():
        sys.path.insert(0, str(local_deps))
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    from matplotlib.lines import Line2D
    from matplotlib.text import Text

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
        'axes.labelsize': 9, 'axes.titlesize': 10, 'xtick.labelsize': 8,
        'ytick.labelsize': 8, 'legend.fontsize': 8, 'pdf.fonttype': 42,
        'ps.fonttype': 42, 'svg.fonttype': 'none', 'axes.spines.top': False,
        'axes.spines.right': False, 'axes.linewidth': .7, 'savefig.dpi': 300})
    sources = {}
    checks = []
    errors = []
    def load(folder, filename):
        p = ws / '进度' / folder / filename
        data = p.read_bytes()
        sources[p.relative_to(ws).as_posix()] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        return json.loads(data)
    def close(a, b, name):
        diff = float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
        if diff > 1e-10 or not np.isfinite(diff):
            raise ValueError(f'{name}: max error {diff}')
        errors.append(diff)
    src = 'static-emotion-v2-20261008'
    ext = 'pmemo-external-v1-20261008'
    exp = 'target-expansion-v2-20261008'
    source = load(src, 'summary.json')
    config = load(src, 'config.json')
    constant = load(src, 'constant-baseline.json')
    summary = load(ext, 'summary.json')
    audit = load(ext, 'audit-local.json')
    boot = load(ext, 'bootstrap-local.json')
    split = load(ext, 'frozen-split.json')
    episodes = load(ext, 'episodes.json')
    expansion = load(exp, 'primary-bootstrap.json')
    expansion_summary = load(exp, 'summary.json')
    expansion_audit = load(exp, 'local-audit.json')
    expansion_split = load(exp, 'frozen-split.json')
    expansion_episodes = load(exp, 'episodes.json')
    assert audit['status'] == expansion_audit['status'] == 'PASS'
    axes_names = ['valence', 'arousal']
    methods = split['methods']
    budgets = split['budgets']
    seeds = split['seeds']
    draw_ids = sorted({e['draw'] for e in episodes})
    eval_ids = [r['music_id'] for r in split['evaluation_rows']]
    adapt_ids = {r['music_id'] for r in split['adaptation_rows']}
    assert set(adapt_ids).isdisjoint(eval_ids)
    assert len(set(eval_ids)) == len(eval_ids) == audit['evaluation_groups']
    assert len(episodes) == len(seeds) * len(draw_ids) * len(budgets)
    assert methods == ['none', 'offset', 'affine', 'half_offset', 'arousal_only_half']
    constant_error = np.mean([(np.array(r['prediction'])-r['target'])**2 for r in constant['rows']], axis=0)
    close(constant_error, [constant['validation'][a]['mse'] for a in axes_names], 'constant per-track reconstruction')
    for a in axes_names:
        close(constant['validation'][a]['mse'], source['constant_baseline'][a]['mse'], 'constant summary')
    stats = {(r['budget'], r['method']): r for r in summary}
    bootstrap_stats = {(r['budget'], r['method'], r['axis']): r for r in boot['all_results']}
    indices = np.array(boot['shared_resampling_indices'], dtype=int)
    assert indices.shape == (boot['repetitions'], len(eval_ids))
    assert boot['eval_ids'] == eval_ids
    assert boot['eval_group_keys'] == [r['group_key'] for r in split['evaluation_rows']]
    per_track = {}
    for budget in budgets:
        selected = sorted([e for e in episodes if e['budget'] == budget], key=lambda e:(e['seed'], e['draw']))
        assert len({(e['seed'], e['draw']) for e in selected}) == len(seeds)*len(draw_ids)
        for e in selected:
            assert e['eval_ids'] == eval_ids
            assert len(e['adapt_ids']) == budget and set(e['adapt_ids']) <= adapt_ids
            assert set(e['adapt_ids']).isdisjoint(eval_ids)
        for method in methods:
            mse = []
            delta = []
            for e in selected:
                y = np.array(e['target'], dtype=float)
                pred = np.array(e['methods'][method]['prediction'], dtype=float)
                base = np.array(e['methods']['none']['prediction'], dtype=float)
                se = (pred-y)**2
                d = se-(base-y)**2
                close(se.mean(axis=0), [e['methods'][method]['metrics'][a]['mse'] for a in axes_names], 'episode MSE')
                close(d.mean(axis=0), e['methods'][method]['delta_mse'], 'episode delta')
                mse.append(se)
                delta.append(d)
            mean_mse = np.mean(mse, axis=(0,1))
            mean_d = np.mean(delta, axis=0)
            per_track[(budget, method)] = mean_d
            close(mean_mse, [stats[(budget,method)]['metrics'][a]['mse'] for a in axes_names], 'external summary')
            close(mean_d.mean(axis=0), stats[(budget,method)]['mean_delta_mse'], 'summary paired delta')
            for k,a in enumerate(axes_names):
                r = bootstrap_stats[(budget,method,a)]
                close(mean_d[:,k], r['paired_per_track_delta_mse'], 'paired per-track bootstrap input')
                ci = np.percentile(mean_d[:,k][indices].mean(axis=1), [2.5,97.5], method=boot['percentile_method'])
                close(ci, r['ci95'], 'saved shared-group bootstrap replay')
                close(ci, next(t for t in [audit['primary']]+audit['secondary'] if (t['budget'],t['method'],t['axis'])==(budget,method,a))['ci95'], 'audit CI')
    checks.append('PMEmo: all episode MSE, summary means, paired track deltas and all 20 saved bootstrap CIs reconstructed from predictions.')
    primary = boot['primary']
    assert (primary['budget'],primary['method'],primary['axis']) == (10,'arousal_only_half','arousal')
    primary_eps = sorted([e for e in episodes if e['budget']==primary['budget']], key=lambda e:(e['seed'],e['draw']))
    pool_deltas = np.array([e['methods'][primary['method']]['delta_mse'][1] for e in primary_eps]).reshape(len(seeds),len(draw_ids))
    for i, s in enumerate(seeds):
        close(pool_deltas[i], next(r for r in primary['per_seed'] if r['seed']==s)['pool_delta_mse'], 'pool delta replay')
    worsened = int((pool_deltas>0).sum())
    assert worsened == primary['pools_worsened'] == audit['primary']['pools_worsened']
    expansion_values = []
    for h in expansion['hypotheses']:
        selected = [e for e in expansion_episodes if e['genre']==h['genre'] and e['budget']==h['budget']]
        k = axes_names.index(h['axis'])
        ds = []
        for e in selected:
            y = np.asarray(e['target'])
            pred = np.asarray(e['methods'][h['method']]['prediction'])
            base = np.asarray(e['methods']['none']['prediction'])
            ds.append(((pred-y)**2-(base-y)**2)[:,k])
        track = np.mean(ds,axis=0)
        assert len(track)==h['eval_count']
        close(track,h['track_delta'],'DEAM expansion track delta replay')
        close(track.mean(),h['mean_delta_mse'],'DEAM expansion mean replay')
        r = next(r for r in expansion_summary if (r['genre'],r['budget'],r['method'])==(h['genre'],h['budget'],h['method']))
        close(track.mean(),r['mean_delta_mse'][k],'DEAM expansion summary')
        assert h['ci95'][0] < 0 < h['ci95'][1]
        expansion_values.append({key:h[key] for key in ['genre','method','budget','axis','eval_count','mean_delta_mse','ci95','ci98_333']})
    checks.append('DEAM expansion: each fixed hypothesis track delta and summary mean reconstructed; all saved 95% intervals cross zero. Saved expansion bootstrap draws are not present, so CI endpoints are traced to primary-bootstrap.json, not recomputed.')
    colors = ['#666666','#0072B2','#E69F00','#009E73','#CC79A7']
    markers = ['o','s','^','D','P']
    names = {'none':'None', 'offset':'Offset', 'affine':'Affine', 'half_offset':'Half offset', 'arousal_only_half':'Arousal-only\nhalf offset'}
    files = []
    captions = {}
    values = {}
    def save(fig, name, caption, data):
        fig.canvas.draw()
        texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
        assert min(t.get_fontsize() for t in texts) >= 8
        records=[]
        for suffix in ['png','pdf','svg']:
            p = out / f'{name}.{suffix}'
            fig.savefig(p, dpi=300, bbox_inches='tight', pad_inches=.09)
            records.append({'filename':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
        files.append({'figure':name,'files':records,'minimum_font_pt':min(t.get_fontsize() for t in texts), 'nominal_width_inches':fig.get_size_inches()[0]})
        captions[name]=caption
        values[name]=data
        plt.close(fig)
    def style(ax):
        ax.grid(axis='y', color='#e5e5e5',linewidth=.55)
        ax.set_axisbelow(True)
    ntrain,nval,nadapt,neval = len(config['train_ids']),len(config['validation_ids']),len(adapt_ids),len(eval_ids)
    nexp = expansion_audit['new_evaluation_tracks']
    fig, ax = plt.subplots(figsize=(7.15,4.3))
    fig.subplots_adjust(left=.015,right=.985,top=.97,bottom=.03)
    ax.set(xlim=(0,1),ylim=(0,1)); ax.axis('off')
    def box(x,y,w,h,text,color='#0072B2',dashed=False):
        patch=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',facecolor='#f8f9fa',edgecolor=color,linewidth=1,linestyle='--' if dashed else '-')
        ax.add_patch(patch);ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9,linespacing=1.45)
    def arrow(start,end,label=None):
        ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'-|>','color':'#333333','lw':1.1})
        if label:ax.text((start[0]+end[0])/2,(start[1]+end[1])/2+.025,label,ha='center',va='bottom',fontsize=8)
    ax.text(.02,.965,'(a) Source development: DEAM official static overall emotion',fontsize=10)
    box(.02,.735,.25,.16,f'Train: {ntrain} excerpts\nFit prediction heads\nMERT features frozen')
    box(.37,.735,.25,.16,f'Validation: {nval} excerpts\nCheckpoint selection only\nNo final-test claim')
    box(.72,.735,.26,.16,'Freeze source predictor\nMERT + mean_mlp\nNo target neural training')
    arrow((.275,.815),(.36,.815));arrow((.63,.815),(.71,.815))
    ax.text(.02,.635,'(b) Main external validation: PMEmo complete choruses',fontsize=10)
    box(.02,.385,.25,.17,f'Adaptation candidates\n{nadapt} identity groups\nDisjoint from evaluation',color='#009E73')
    box(.37,.385,.25,.17,f'Output calibration only\n{budgets[0]} or {budgets[1]} rated songs\n{len(seeds)} seeds x {len(draw_ids)} shared draws',color='#009E73')
    box(.72,.385,.26,.17,f'Evaluation: {neval} groups\nPaired method vs. none\nNever used to fit correction',color='#009E73')
    arrow((.275,.47),(.36,.47));arrow((.63,.47),(.71,.47))
    arrow((.85,.725),(.85,.565))
    ax.text(.86,.645,'Frozen\npredictions',fontsize=8,va='center')
    ax.text(.02,.265,'(c) Auxiliary development evidence: separate from external main test',fontsize=10)
    box(.02,.045,.96,.155,f'DEAM expansion: {nexp} new tracks (country / pop)\nSeparate historical genre-specific models and fixed calibration policies\nAuxiliary stage only; not PMEmo data, not an independent external test',color='#666666',dashed=True)
    save(fig,'fig01_protocol','Source development and external output calibration use disjoint data roles. DEAM supplies official static overall-emotion labels for the training and model-selection validation excerpts; Music Embedding Representation from Transformers (MERT) features remain frozen and mean_mlp is a mean-pooled multilayer-perceptron prediction head. After freezing the source predictors, calibration fits only the rated adaptation songs from the PMEmo candidate groups, and the complete-chorus evaluation groups never fit the correction. The separate DEAM country/pop expansion is auxiliary development evidence using historical genre-specific models and has no arrow into the PMEmo main external evaluation; this is an applied empirical study, not an original-algorithm claim.',{'train':ntrain,'validation':nval,'adaptation_candidates':nadapt,'external_evaluation':neval,'auxiliary_expansion':nexp,'budgets':budgets})
    fig,axs=plt.subplots(1,2,figsize=(7.15,3.15),sharey=True)
    fig.subplots_adjust(left=.09,right=.985,top=.87,bottom=.25,wspace=.17)
    source_values={}
    model_labels=['Constant\n(single)','Mean\nlinear','Mean\nMLP','Attention\nMLP']
    for k,a in enumerate(axes_names):
        ax=axs[k];means=[constant['validation'][a]['mse']]
        source_values[a]={}
        for model in config['models']:
            rs=sorted([r for r in source['runs'] if r['model']==model],key=lambda r:r['seed'])
            assert [r['seed'] for r in rs]==config['seeds']
            pts=[r['validation'][a]['mse'] for r in rs];means.append(float(np.mean(pts)));source_values[a][model]={'mean':means[-1],'seeds':pts}
        ax.bar(range(4),means,color=['#b5b5b5','#56B4E9','#0072B2','#E69F00'],edgecolor='#444444',width=.63,linewidth=.6)
        for j,model in enumerate(config['models'],1):
            for i,v in enumerate(source_values[a][model]['seeds']):ax.plot(j+(i-1)*.14,v,marker=markers[i],color='black',ms=4,linestyle='none')
        ax.plot(0,means[0],marker='x',color='black',ms=5)
        for j,v in enumerate(means):ax.text(j,v+.0045,f'{v:.4f}',ha='center',fontsize=8)
        ax.set_xticks(range(4),model_labels);ax.set_ylim(0,max(constant_error)*1.23)
        ax.set_title(f'({chr(97+k)}) {a.title()}',loc='left');style(ax)
    axs[0].set_ylabel('Validation MSE (normalized rating²)')
    fig.legend([Line2D([],[],marker=markers[i],color='black',ls='none',ms=4) for i in range(len(seeds))], [f'Seed {s}' for s in seeds],loc='upper center',bbox_to_anchor=(.53,1),ncol=len(seeds),frameon=False)
    save(fig,'fig02_source_baselines','Frozen-MERT prediction heads have lower source-validation mean squared error (MSE) than the training-mean constant predictor on both emotion axes. Bars show the mean over the three actual training seeds and the marker shapes show each seed separately; the deterministic constant baseline is a single result and has no replicated seed points or error bar. Labels show four-decimal MSE in squared normalized-rating units, with all bars starting at zero. DEAM validation is development/model-selection evidence, not an independent final test; MLP means multilayer perceptron.',source_values)
    fig,axs=plt.subplots(1,2,figsize=(7.15,3.25),sharey=True)
    fig.subplots_adjust(left=.09,right=.985,top=.86,bottom=.3,wspace=.17)
    for k,a in enumerate(axes_names):
        ax=axs[k]
        for bi,budget in enumerate(budgets):
            x=np.arange(len(methods))+(bi-.5)*.34
            vals=[stats[(budget,m)]['metrics'][a]['mse'] for m in methods]
            ax.bar(x,vals,width=.31,color=['#56B4E9','#E69F00'][bi],edgecolor='#444444',linewidth=.5,alpha=.65)
            ax.plot(x,vals,ls='none',marker=['o','s'][bi],color=['#0072B2','#805600'][bi],ms=3.5)
            for xx,v in zip(x,vals):ax.text(xx,v+.003,f'{v:.3f}',ha='center',fontsize=8,rotation=90)
        ax.set_xticks(range(len(methods)),[names[m] for m in methods],rotation=25,ha='right')
        ax.set_ylim(0,max(r['metrics'][a]['mse'] for r in summary for a in axes_names)*1.35)
        ax.set_title(f'({chr(97+k)}) {a.title()}',loc='left');style(ax)
    axs[0].set_ylabel('External MSE (normalized rating²)')
    fig.legend([Line2D([],[],color=['#0072B2','#805600'][i],marker=['o','s'][i],lw=5) for i in range(len(budgets))],[f'{b} rated songs' for b in budgets],loc='upper center',ncol=2,frameon=False)
    save(fig,'fig03_external_methods','Output calibration reduces average PMEmo external MSE, while the arousal-only half-offset leaves valence unchanged by design. Both panels include all five fixed methods and both rating budgets, with averages over three frozen source-model seeds and ten shared adaptation draws on the same complete-chorus evaluation groups. The uncalibrated none method is deliberately repeated for both budgets, as it is budget-independent. These means describe repeated conditions on one shared evaluation set, not thirty independent datasets; paired uncertainty is shown in Figure 4.',summary)
    fig,axs=plt.subplots(1,2,figsize=(7.15,3.45),sharex=True)
    fig.subplots_adjust(left=.19,right=.975,top=.88,bottom=.27,wspace=.12)
    interval_values=[]
    for k,a in enumerate(axes_names):
        ax=axs[k]
        for j,m in enumerate(methods):
            r=bootstrap_stats[(primary['budget'],m,a)];low,high=r['ci95'];mid=r['delta_mse']
            ax.errorbar(mid,j,xerr=[[mid-low],[high-mid]],marker=markers[j],color=colors[j],mfc=colors[j] if (m,a)==('arousal_only_half','arousal') else 'white',ms=6,capsize=3,linestyle='none',lw=1.25)
            interval_values.append({'method':m,'axis':a,'delta_mse':mid,'ci95':[low,high]})
        ax.axvline(0,color='#444444',ls='--',lw=1)
        ax.set_yticks(range(len(methods)),[names[m]+('\nPRIMARY' if m=='arousal_only_half' and a=='arousal' else '') for m in methods] if k==0 else ['None','Offset','Affine','Half offset','Arousal-only\nhalf offset: PRIMARY'])
        if k==1:ax.tick_params(axis='y',labelleft=False)
        ax.set_ylim(len(methods)-.5,-.5);ax.set_title(f'({chr(97+k)}) {a.title()}',loc='left')
        ax.grid(axis='x',color='#e5e5e5',lw=.55)
    fig.text(.5,.985,'Primary: arousal-only half offset on arousal (filled marker); all other contrasts secondary',ha='center',va='top',fontsize=8)
    fig.supxlabel('ΔMSE = method − none (normalized rating²); negative = improvement',fontsize=9,y=.12)
    fig.text(.5,.025,f'{primary["budget"]}-song budget | paired group bootstrap, 95% CI | secondary intervals unadjusted',ha='center',fontsize=8)
    save(fig,'fig04_paired_intervals','The prespecified ten-song arousal-only half-offset contrast improves average PMEmo arousal MSE, with its paired 95% interval below zero. Horizontal intervals use the saved evaluation-identity-group bootstrap, averaging paired squared-error differences over the three frozen seeds and ten shared adaptation draws before resampling the evaluation groups; the resampling unit is a group representative, not a seed/draw condition. Only arousal_only_half on arousal at budget ten is primary (filled marker); every other contrast, including all valence contrasts, is secondary with unadjusted 95% intervals and no multiplicity-controlled significance claim. Negative method-minus-none differences mean improvement, and units are squared normalized ratings; these intervals are conditional on the fixed models, adaptation candidate pool and draws, not uncertainty over new model training or newly sampled datasets.',interval_values)
    fig,ax=plt.subplots(figsize=(7.15,3.25))
    fig.subplots_adjust(left=.12,right=.98,top=.85,bottom=.24)
    for i,s in enumerate(seeds):
        ax.plot(np.array(draw_ids)+1+(i-1)*.12,pool_deltas[i],marker=markers[i],color=colors[i+1],ls='none',ms=6,label=f'Seed {s}')
    ax.axhline(0,color='#444444',ls='--',lw=1)
    ax.set_xticks(np.array(draw_ids)+1);ax.set_xlabel('Shared adaptation draw (same candidate pool and evaluation groups)')
    ax.set_ylabel('Paired arousal ΔMSE\n(method − none; normalized rating²)');style(ax)
    ax.legend(loc='lower right',frameon=False,ncol=3)
    fig.text(.55,.99,f'{primary["budget"]} rated songs | arousal-only half offset\n{worsened}/{pool_deltas.size} seed–draw conditions worsen; not independent datasets',ha='center',va='top',fontsize=9)
    save(fig,'fig05_pool_stability',f'The primary arousal-only half-offset improves PMEmo arousal MSE in {pool_deltas.size-worsened} of {pool_deltas.size} seed–draw conditions, but {worsened} conditions worsen. Points show the ten-song method-minus-none paired MSE for each of the three source-model seeds and ten shared adaptation draws; the same draw indices use shared adaptation song subsets across seeds and all points reuse the same candidate pool and evaluation groups. Thus the {pool_deltas.size} points are dependent repeated conditions, not {pool_deltas.size} independent datasets or an independent-sample significance test. The horizontal zero line denotes no change, and negative squared normalized-rating differences mean improvement.',{'seeds':seeds,'draws':draw_ids,'delta_mse':pool_deltas.tolist(),'worsened':worsened})
    fig,ax=plt.subplots(figsize=(7.15,2.65))
    fig.subplots_adjust(left=.28,right=.97,top=.86,bottom=.28)
    for j,h in enumerate(expansion_values):
        v=h['mean_delta_mse'];lo,hi=h['ci95']
        ax.errorbar(v,j,xerr=[[v-lo],[hi-v]],marker=markers[j],color=colors[j+1],mfc='white',ms=7,capsize=4,ls='none',lw=1.3)
    ax.axvline(0,color='#444444',ls='--',lw=1)
    ax.set_yticks(range(len(expansion_values)),[f'{h["genre"].title()} (n={h["eval_count"]})\n{h["axis"].title()}: {h["method"].replace("_"," ")}' for h in expansion_values])
    ax.set_ylim(len(expansion_values)-.5,-.5)
    ax.set_xlabel('ΔMSE = method − none (normalized rating²)')
    ax.grid(axis='x',color='#e5e5e5',lw=.55)
    ax.text(.5,1.075,f'Auxiliary DEAM expansion | {primary["budget"]}-song fixed policies | all 95% CIs cross zero',transform=ax.transAxes,ha='center',fontsize=9)
    save(fig,'fig06_deam_expansion','The auxiliary DEAM expansion does not establish a reliable improvement: all three fixed-policy 95% intervals cross zero. Country evaluates affine correction on valence and arousal over 43 new tracks, and pop evaluates half-offset correction on arousal over 31 new tracks, each at the ten-song budget with fixed historical genre-specific source models and adaptation draws. Intervals are saved song-group bootstrap results conditional on the fixed models and pools; these three auxiliary hypotheses have unadjusted 95% intervals (the source also records 98.333% intervals), so no multiplicity-controlled superiority is claimed. This negative auxiliary result is retained separately from the PMEmo main external validation; the historical source set is not fully traceable, as documented in the bootstrap source.',expansion_values)
    for path, record in sources.items():
        assert hashlib.sha256((ws/path).read_bytes()).hexdigest() == record['sha256'], f'Source changed during generation: {path}'
    manifest={'schema':'paper-figures-v1','study_type':'applied empirical; no original algorithm claim',
        'generator':{'path':'lunwen2/scripts/generate_figures.py','sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'environment':{'python':sys.version,'numpy':np.__version__,'matplotlib':matplotlib.__version__},
        'sources':sources,'source_sha256_unchanged_after_generation':True,'checks':checks,
        'max_abs_numeric_reconstruction_error':max(errors),'absolute_tolerance':1e-10,
        'figures':files,'plotted_values':values,
        'track_provenance':{'deam_train_ids':config['train_ids'],'deam_validation_ids':config['validation_ids'],
            'pmemo_evaluation_ids':eval_ids,'pmemo_evaluation_group_keys':boot['eval_group_keys'],
            'pmemo_adaptation_ids':sorted(adapt_ids),'pmemo_audio_sha256':{str(r['music_id']):r['audio_sha256'] for r in split['adaptation_rows']+split['evaluation_rows']},
            'pmemo_bootstrap_indices_sha256_recorded':boot['resampling_indices_sha256'],
            'deam_expansion_frozen_split':expansion_split},
        'limitations':['Local numerical replay, not new raw audio inference or training.',
            'Source validation is development evidence; mean_mlp is not presented as the best architecture.',
            'Group-bootstrap intervals condition on frozen models and the shared adaptation pool/draws.',
            'Secondary PMEmo and auxiliary DEAM 95% intervals are unadjusted.',
            'DEAM expansion saved bootstrap CI endpoints traced; resampling indices absent.',
            'DEAM expansion historical205 is not fully traceable.'],
        'publication_insertion':'Use PDF/SVG at nominal width (7.15 inches) or larger; min text 8 pt. Do not reduce to one column without regenerating larger text.',
        'visual_review':'PNG visual review is performed after generation, separately from numerical checks.'}
    (out/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    header='# Paper figure captions\n\nAll figures use English labels, 300-dpi PNG previews and native-vector PDF/SVG exports. Insert at nominal 7.15-inch full-page/two-column width or larger to preserve the minimum 8-point font; regenerate rather than shrink to a single column. MSE denotes mean squared error and CI denotes confidence interval. Normalized emotion ratings use the experiment scale, not percentage errors.\n\n'
    (out/'captions.md').write_text(header+'\n\n'.join(f'## {n}\n\n{c}' for n,c in captions.items())+'\n',encoding='utf-8')
    print(json.dumps({'generated':[f['figure'] for f in files],'formats':['PNG 300 dpi','PDF','SVG'],'source_files_sha256_verified':len(sources),'max_abs_numeric_error':max(errors),'primary_delta_mse':primary['delta_mse'],'primary_ci95':primary['ci95'],'pool_conditions_worsened':worsened,'limitations':manifest['limitations']},indent=2))


if __name__ == '__main__':
    main()
