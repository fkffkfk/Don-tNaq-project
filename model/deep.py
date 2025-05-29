import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
import seaborn as sns
import tensorflow as tf
from tensorflow.keras.layers import Dropout



# 학습 성능 시각화

def plot_history(history):
    plt.figure(figsize=(10,4))

    # Accuracy
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='train acc') # 학습 데이터 정확도
    plt.plot(history.history['val_accuracy'], label='val acc')#검증 데이터 정확도
    plt.title('Accuracy')
    plt.legend()

    # Loss
    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='train loss')
    plt.plot(history.history['val_loss'], label='val loss')
    plt.title('Loss')
    plt.legend()

    plt.tight_layout()
    plt.show()
    plt.close()
    

# 테스트 마치고 시각화 코드
def plot_confusion_matrix(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Benign', 'Malicious'],
                yticklabels=['Benign', 'Malicious'])
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.show()
    plt.close()
    

# 0. 재현성 고려
np.random.seed(42)
tf.random.set_seed(42) 

# ---------------------------------------------
# 1) CSV에서 train/test 데이터 불러오기
train_df = pd.read_csv('train.csv')  
train_df.dropna(subset=['URL','라벨링 이름'], inplace=True)
test_df  = pd.read_csv('test.csv')
test_df.dropna(subset=['URL','라벨링 이름'], inplace=True)

train_urls   = train_df['URL'].astype(str).tolist()
train_labels = train_df['is_malicious'].astype(int).tolist()
test_urls    = test_df ['URL'].astype(str).tolist()
test_labels  = test_df ['is_malicious'].astype(int).tolist()

# ---------------------------------------------
# 2) 문자열 기준 URL 길이 분포로 maxlen 설정 (95 percent)
all_lengths = [len(u) for u in train_urls]  # 문자열 길이 계산
maxlen      = int(np.ceil(np.percentile(all_lengths, 95)))   # 95% URLs 커버
print(f"✅ maxlen (95%) = {maxlen}")

# ---------------------------------------------
# 3) 문자 단위 Tokenizer(각 문자로 쪼갬) 및 정수 시퀀스 변환
tokenizer = Tokenizer(char_level=True, oov_token=None)
tokenizer.fit_on_texts(train_urls)           # 오직 train 기준으로 단어장 구축

train_seq = tokenizer.texts_to_sequences(train_urls)
test_seq  = tokenizer.texts_to_sequences(test_urls)

# ---------------------------------------------
# 4) 패딩
X_train = pad_sequences(train_seq, maxlen=maxlen, padding='post', truncating='post')
X_test  = pad_sequences(test_seq,  maxlen=maxlen, padding='post', truncating='post')
y_train = np.array(train_labels)
y_test  = np.array(test_labels)


# 5) 학습
# 단어 집합 크기 (char-level tokenizer 기준)
vocab_size = len(tokenizer.word_index) + 1  # +1 for padding(0번)

# 모델 정의
model = Sequential()
model.add(Embedding(input_dim=vocab_size, output_dim=128, input_length=maxlen))  # 128차원 임베딩
model.add(Conv1D(filters=64, kernel_size=5, strides=1, activation='relu'))
model.add(GlobalMaxPooling1D())  # 가장 강한 신호 하나만 남김
model.add(Dropout(0.5))          # 과적합 방지용
model.add(Dense(32, activation='relu'))
model.add(Dense(1, activation='sigmoid'))  # 이진 분류 (0/1)

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# 모델 학습
history = model.fit(X_train, y_train, epochs=10, batch_size=128, validation_split=0.2, verbose=1)


# 6) 학습 성능 시각화

plot_history(history) 



    
# 7)테스트 후 시각화
y_pred = (model.predict(X_test) > 0.5).astype(int)
print(classification_report(y_test, y_pred, target_names=['Benign','Malicious']))
plot_confusion_matrix(y_test, y_pred)
