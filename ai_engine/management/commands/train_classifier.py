from pathlib import Path
from django.core.management.base import BaseCommand
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
import joblib
from ai_engine.classifier import MODEL_PATH, preprocess_text
class Command(BaseCommand):
    help='Train TF-IDF + Linear SVM classifier from sample_documents/<Category>/*.txt'
    def handle(self,*args,**kwargs):
        root=Path('sample_documents'); texts=[]; labels=[]
        for category_dir in root.iterdir() if root.exists() else []:
            if category_dir.is_dir():
                for f in category_dir.glob('*.txt'):
                    texts.append(preprocess_text(f.read_text(encoding='utf-8',errors='ignore'))); labels.append(category_dir.name)
        if len(set(labels))<2:
            self.stdout.write(self.style.WARNING('Not enough labelled samples. Add text files inside sample_documents/<Category>/')) ; return
        vectorizer=TfidfVectorizer(stop_words='english', max_features=5000)
        X=vectorizer.fit_transform(texts); model=LinearSVC(); model.fit(X,labels)
        joblib.dump({'vectorizer':vectorizer,'model':model,'labels':sorted(set(labels))}, MODEL_PATH)
        self.stdout.write(self.style.SUCCESS(f'Trained classifier on {len(texts)} samples. Saved to {MODEL_PATH}'))
