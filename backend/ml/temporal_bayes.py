"""Smoothed discrete NB/TAN for local longitudinal research, not clinical use.

Quantile edges, the dependency tree and all probability tables are fitted using
training infants only. Missingness is an explicit state, never a normal value.
TAN edges are statistical dependencies, not causal or guideline relationships.
"""
from __future__ import annotations
import math
import numpy as np


class TemporalBayes:
    def __init__(self,tree=True,equivalent_sample_size=10.):
        self.tree=tree;self.ess=float(equivalent_sample_size)
        if not math.isfinite(self.ess) or self.ess<=0:raise ValueError('Invalid prior strength')

    def _states(self,x):
        x=np.asarray(x,dtype=float)
        if x.ndim!=2 or x.shape[1]!=len(self.edges) or np.isinf(x).any():raise ValueError('Invalid Bayesian input matrix')
        return np.column_stack([np.where(np.isnan(x[:,j]),0,1+np.searchsorted(e,x[:,j],side='right')) for j,e in enumerate(self.edges)]).astype(int)

    @staticmethod
    def _mi(a,b,y,w,ka,kb):
        total=float(w.sum());value=0.
        for label in [0,1]:
            mask=y==label;mass=w[mask].sum()
            if not mass:continue
            counts=np.zeros((ka,kb));np.add.at(counts,(a[mask],b[mask]),w[mask])
            p=counts/mass;den=p.sum(1)[:,None]*p.sum(0)[None,:];ok=p>0
            value+=mass/total*float(np.sum(p[ok]*np.log(p[ok]/den[ok])))
        return value

    def fit(self,x,y,sample_weight=None):
        x=np.asarray(x,dtype=float);y=np.asarray(y)
        if x.ndim!=2 or x.shape[1]<1 or len(x)!=len(y) or set(np.unique(y))!={0,1} or np.isinf(x).any():
            raise ValueError('Training needs finite/explicit-missing predictors and both binary labels')
        w=np.ones(len(x)) if sample_weight is None else np.asarray(sample_weight,dtype=float)
        if len(w)!=len(x) or not np.isfinite(w).all() or (w<=0).any():raise ValueError('Invalid training weights')
        self.edges=[]
        for j in range(x.shape[1]):
            observed=x[np.isfinite(x[:,j]),j]
            unique=np.unique(observed)
            cuts=((unique[:-1]+unique[1:])/2).tolist() if len(unique)<=3 else np.unique(np.quantile(observed,[1/3,2/3])).tolist()
            self.edges.append([float(v) for v in cuts if observed.min()<v<observed.max()])
        states=self._states(x);self.cardinalities=[len(e)+2 for e in self.edges]
        d=x.shape[1];self.parents=[-1]*d
        if self.tree and d>1:
            conditional=np.zeros((d,d))
            for j in range(d):
                for k in range(j):
                    conditional[j,k]=conditional[k,j]=self._mi(states[:,j],states[:,k],y,w,self.cardinalities[j],self.cardinalities[k])
            # Deterministic maximum spanning tree, fixed root 0; no tuning on
            # validation labels or graph search after test results are observed.
            reached={0}
            while len(reached)<d:
                _,parent,child=max((conditional[j,k],-j,-k) for j in reached for k in range(d) if k not in reached)
                parent,child=-parent,-child
                self.parents[child]=parent;reached.add(child)
        class_mass=np.bincount(y.astype(int),weights=w,minlength=2)
        self.class_prior=((class_mass+1)/(w.sum()+2)).tolist();self.tables=[]
        for j,card in enumerate(self.cardinalities):
            global_counts=np.bincount(states[:,j],weights=w,minlength=card)
            pooled=(global_counts+1)/(w.sum()+card)
            marginal=np.zeros((2,card))
            for label in [0,1]:
                mask=y==label;counts=np.bincount(states[mask,j],weights=w[mask],minlength=card)
                marginal[label]=(counts+self.ess*pooled)/(class_mass[label]+self.ess)
            parent=self.parents[j]
            if parent<0:self.tables.append(marginal.tolist());continue
            table=np.zeros((2,self.cardinalities[parent],card))
            for label in [0,1]:
                for state in range(self.cardinalities[parent]):
                    mask=(y==label)&(states[:,parent]==state)
                    counts=np.bincount(states[mask,j],weights=w[mask],minlength=card)
                    table[label,state]=(counts+self.ess*marginal[label])/(w[mask].sum()+self.ess)
            self.tables.append(table.tolist())
        return self

    def predict_proba(self,x):
        states=self._states(x);logs=np.tile(np.log(self.class_prior),(len(states),1))
        for j,parent in enumerate(self.parents):
            table=np.asarray(self.tables[j])
            for label in [0,1]:
                p=table[label,states[:,j]] if parent<0 else table[label,states[:,parent],states[:,j]]
                logs[:,label]+=np.log(p)
        logs-=logs.max(axis=1,keepdims=True);p=np.exp(logs)
        return p/p.sum(axis=1,keepdims=True)

    def to_dict(self):
        return {'kind':'smoothed_tree_augmented_bayes' if self.tree else 'smoothed_naive_bayes',
            'equivalent_sample_size':self.ess,'edges':self.edges,'cardinalities':self.cardinalities,
            'parents':self.parents,'class_prior':self.class_prior,'tables':self.tables,
            'clinical_eos_eligible':False,'probability_calibration':'not independently calibrated'}

    @classmethod
    def from_dict(cls,a):
        if a.get('kind') not in {'smoothed_tree_augmented_bayes','smoothed_naive_bayes'} or a.get('clinical_eos_eligible') is not False:
            raise ValueError('Invalid Bayesian lifecycle/estimator')
        obj=cls(a['kind']=='smoothed_tree_augmented_bayes',a['equivalent_sample_size'])
        for key in ['edges','cardinalities','parents','class_prior','tables']:setattr(obj,key,a[key])
        if len(obj.parents)!=len(obj.edges) or len(obj.tables)!=len(obj.edges):raise ValueError('Invalid Bayesian dimensions')
        prior=np.asarray(obj.class_prior,dtype=float)
        if prior.shape!=(2,) or not np.isfinite(prior).all() or (prior<=0).any() or not np.isclose(prior.sum(),1):raise ValueError('Invalid Bayesian class prior')
        for j in range(len(obj.parents)):
            cuts=obj.edges[j]
            if obj.cardinalities[j]!=len(cuts)+2 or not all(math.isfinite(v) for v in cuts) or any(a>=b for a,b in zip(cuts,cuts[1:])):
                raise ValueError('Invalid Bayesian discretization')
            chain=set();node=j
            while node!=-1:
                if node in chain or not 0<=node<len(obj.parents):raise ValueError('Invalid Bayesian dependency tree')
                chain.add(node);node=obj.parents[node]
            values=np.asarray(obj.tables[j],dtype=float)
            expected=(2,obj.cardinalities[j]) if obj.parents[j]<0 else (2,obj.cardinalities[obj.parents[j]],obj.cardinalities[j])
            if values.shape!=expected or not np.isfinite(values).all() or (values<=0).any() or not np.allclose(values.sum(-1),1):
                raise ValueError('Invalid Bayesian probability table')
        return obj
