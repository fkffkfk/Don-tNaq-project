import pandas as pd
from fix_feature import CountBased
import matplotlib.pyplot as plt

def average_results(r1, r2):
    avg = []
    for a, b in zip(r1, r2):
        t = a[0]
        sm = (a[1] + b[1]) / 2
        nm = (a[2] + b[2]) / 2
        lm = (a[3] + b[3]) / 2
        sb = (a[4] + b[4]) / 2
        nb = (a[5] + b[5]) / 2
        lb = (a[6] + b[6]) / 2
        avg.append((t, sm, nm, lm, sb, nb, lb))
    return avg

def plot_tradeoff_triple(results_benign, results_malicious):
    results_avg = average_results(results_benign, results_malicious)

    def extract_vals(results):
        thresholds = [r[0] for r in results]
        recall = [(r[1] + r[2] + r[3]) / 3 for r in results]
        precision = [(r[4] + r[5] + r[6]) / 3 for r in results]
        f1 = [2 * (p * r) / (p + r) if (p + r) != 0 else 0 for p, r in zip(precision, recall)]
        return thresholds, recall, precision, f1

    tb, rb, pb, fb = extract_vals(results_benign)
    tm, rm, pm, fm = extract_vals(results_malicious)
    ta, ra, pa, fa = extract_vals(results_avg)

    fig, axs = plt.subplots(1, 3, figsize=(18, 5), sharey=True)

    for ax, t, r, p, f, title in zip(
        axs,
        [tb, tm, ta],
        [rb, rm, ra],
        [pb, pm, pa],
        [fb, fm, fa],
        ["Benign-Based", "Malicious-Based", "Average-Based"]
    ):
        max_idx = f.index(max(f))
        ax.plot(t, r, marker='o', label='Recall', color='orange')
        ax.plot(t, p, marker='o', label='Benign Accuracy', color='steelblue')
        ax.plot(t, f, marker='o', label='F1-score', linestyle='--', color='deeppink')
        ax.axvline(x=t[max_idx], linestyle='--', color='gray', label=f'Optimal = {t[max_idx]}')
        ax.scatter([t[max_idx]], [f[max_idx]], color='red', zorder=5)
        ax.set_title(title)
        ax.set_xlabel("Threshold")
        ax.invert_xaxis()
        ax.grid(True)

    axs[0].set_ylabel("Rate (%)")
    axs[2].legend(loc='lower left')
    plt.tight_layout()
    plt.show()
    
# ▒ 데이터 불러오기
df = pd.read_csv("C:/Users/user/졸업/train_dataset.csv")

# ▒ raw 특성 추출
df['schar_raw'] = df['URL'].apply(CountBased.counting_specialchar)
df['num_raw'] = df['URL'].apply(CountBased.extract_num)
df['letter_raw'] = df['URL'].apply(CountBased.extract_letter)

def evaluate_thresholds(df, threshold_list, basis='benign'):
    # 기준 필터링
    if basis == 'benign':
        stat_df = df[df['is_malicious'] == 0]
    elif basis == 'malicious':
        stat_df = df[df['is_malicious'] == 1]
    elif basis == 'average':
        stat_df = df  # 전체 평균 사용
    else:
        raise ValueError("basis는 'benign', 'malicious', 'average' 중 하나여야 합니다.")

    # 기준 이름 출력용
    basis_name = {
        'benign': '정상 URL 기준',
        'malicious': '악성 URL 기준',
        'average': '전체 평균 기준'
    }.get(basis, f"{basis} 기준")

    # 평균/표준편차 계산
    schar_avg = stat_df['schar_raw'].mean()
    schar_std = stat_df['schar_raw'].std()
    num_avg = stat_df['num_raw'].mean()
    num_std = stat_df['num_raw'].std()
    letter_avg = stat_df['letter_raw'].mean()
    letter_std = stat_df['letter_raw'].std()

    results = []

    for th in threshold_list:
        # 열 이름
        cs_col = f'countspecialchar_{basis}_{str(th).replace(".", "")}'
        cn_col = f'countnum_{basis}_{str(th).replace(".", "")}'
        cl_col = f'countletter_{basis}_{str(th).replace(".", "")}'

        # 레벨링
        df[cs_col] = df['schar_raw'].apply(lambda x: CountBased.check_count_level(x, schar_avg, schar_std, threshold=th))
        df[cn_col] = df['num_raw'].apply(lambda x: CountBased.check_count_level(x, num_avg, num_std, threshold=th))
        df[cl_col] = df['letter_raw'].apply(lambda x: CountBased.check_count_level(x, letter_avg, letter_std, threshold=th))

        # 분리
        mal = df[df['is_malicious'] == 1]
        ben = df[df['is_malicious'] == 0]

        # 비율 계산
        sm = (mal[cs_col] == 1).mean() * 100
        nm = (mal[cn_col] == 1).mean() * 100
        lm = (mal[cl_col] == 1).mean() * 100

        sb = (ben[cs_col] == 0).mean() * 100
        nb = (ben[cn_col] == 0).mean() * 100
        lb = (ben[cl_col] == 0).mean() * 100

        results.append((th, sm, nm, lm, sb, nb, lb))

    # 출력
    print(f"\n📊 [{basis_name}]")
    for th, sm, nm, lm, sb, nb, lb in results:
        print(f"\n✅ [± {th} * std 기준]")
        print(f"▸ 특수문자: 악성 탐지율 {sm:.2f}%, 정상 판정률 {sb:.2f}%")
        print(f"▸ 숫자    : 악성 탐지율 {nm:.2f}%, 정상 판정률 {nb:.2f}%")
        print(f"▸ 문자    : 악성 탐지율 {lm:.2f}%, 정상 판정률 {lb:.2f}%")

    return results


# ▒ 실행: 3기준 다 평가
thresholds = [0.5, 0.3, 0.2, 0.1]
results_benign = evaluate_thresholds(df, thresholds, basis='benign')
results_malicious = evaluate_thresholds(df, thresholds, basis='malicious')
results_average = evaluate_thresholds(df, thresholds, basis='average')

plot_tradeoff_triple(results_benign, results_malicious)













