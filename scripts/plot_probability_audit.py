"""Scientific figures from saved aggregate diagnostics, without patient rows."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]

def main():
    a=json.loads((ROOT/'output/research/probability_audit/audit.json').read_text())
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','savefig.facecolor':'white'})
    fig,axs=plt.subplots(2,2,figsize=(11,8.6),layout='constrained')
    teal='#087f8c';navy='#16324f';amber='#b35d12'
    x=np.linspace(.00001,.99999,1000);c=a['calibration']
    y=1/(1+np.exp(-(c['slope']*np.log(x/(1-x))+c['intercept'])))
    ax=axs[0,0];ax.plot(x,y,color=teal,label='Fitted calibration')
    ax.plot([0,1],[0,1],'--',color='#86939d',label='Identity')
    ax.scatter([a['demo']['raw_forest_probability']],[a['demo']['calibrated_supplied_label_probability']],
               color=amber,zorder=5,label='Synthetic demo')
    ax.set(title='A  Calibration sharpens extreme scores',xlabel='Raw forest score',
           ylabel='Calibrated supplied-label score',xlim=(0,1),ylim=(0,1.03));ax.legend(fontsize=8,loc='upper left')
    ax=axs[0,1];ax.plot([0,1],[0,1],'--',color='#86939d')
    for name,color,marker in [('raw',amber,'o'),('calibrated',teal,'s')]:
        bs=a['model_test_'+name]['bins']
        ax.scatter([b['predicted'] for b in bs],[b['observed'] for b in bs],
                   s=[12+3*np.sqrt(b['n']) for b in bs],color=color,marker=marker,alpha=.75,label=name.title())
    ax.set(title='B  Internal reliability on supplied labels',xlabel='Mean predicted score',
           ylabel='Observed supplied-label fraction',xlim=(-.02,1.02),ylim=(-.02,1.04))
    ax.legend(fontsize=8,loc='lower right');ax.text(.03,.94,'n=1,598; marker area reflects bin count\nSome middle bins contain only 3–12 rows',
        transform=ax.transAxes,fontsize=8,va='top')
    ax=axs[1,0];names=['PCT','Oxygen','CRP','Lactate']
    vals=[a['single_feature_diagnostics'][n]['test_auroc_oriented_on_fit'] for n in names]
    bars=ax.barh(names[::-1],vals[::-1],color=teal,height=.55)
    ax.set(title='C  Single variables strongly separate labels',xlabel='Test AUC (orientation selected on fit)',xlim=(.5,1.04))
    for b,v in zip(bars,vals[::-1]):ax.text(v+.006,b.get_y()+b.get_height()/2,f'{v:.3f}',va='center',fontsize=9)
    ax=axs[1,1];labels=['Original demo','Replace labs','Replace vitals','Replace both','Labs unknown']
    vals=[r['supplied_label_probability'] for r in a['demo']['counterfactuals']]
    bars=ax.barh(labels[::-1],vals[::-1],color=[teal]*4+[amber],height=.55)
    ax.set(title='D  Input sensitivity, not treatment effects',xlabel='Calibrated supplied-label score',xlim=(0,1.25))
    for b,v in zip(bars,vals[::-1]):ax.text(v+.02,b.get_y()+b.get_height()/2,f'{v:.5f}',va='center',fontsize=9)
    fig.suptitle('NeoGuard model audit: high internal discrimination is not clinical EOS validation',
                 fontsize=14,fontweight='bold',color=navy)
    target=ROOT/'output/research/figures/probability_audit.png';target.parent.mkdir(exist_ok=True)
    fig.savefig(target,dpi=200);plt.close(fig);print(target)

if __name__=='__main__':main()
