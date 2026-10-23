"""
Tableau de bord VaR et stress test pour un portefeuille de 1 M$.

Pour lancer l'application :
    pip install -r requirements.txt
    streamlit run app.py

Ce que vous allez voir : la perte maximale attendue sur une journée "normale" (la VaR),
la perte dans un scénario de crise (le stress test), et un résumé que l'on peut montrer à un client.
"""
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from statistics import NormalDist

# ------------------------------------------------------------------
# 1. Les fonctions de calcul
#    Nous les gardons séparées de l'affichage pour que vous puissiez les lire (et les tester) facilement.
# ------------------------------------------------------------------

def simulate_returns(mu, sigma, days, seed=0):
    """Nous simulons des rendements quotidiens : R_t = mu + sigma * Z_t, avec Z_t ~ N(0, 1).

    Avec mu = 0 et sigma = 1 %, vous obtenez des rendements centrés sur 0,
    qui varient typiquement de quelques pourcents vers le haut ou le bas.
    """
    rng = np.random.default_rng(seed)       # la graine fixe le tirage : même graine, mêmes résultats
    return mu + sigma * rng.standard_normal(days)


def calc_var(returns, alpha, notional):
    """Nous calculons la VaR historique à alpha (par exemple 0,95).

    Étape 1 : on transforme chaque rendement en perte en dollars, L = -notional * R
              (une perte positive veut dire que l'on perd de l'argent).
    Étape 2 : on prend le percentile alpha de ces pertes. C'est le niveau que la perte
              ne dépasse pas dans alpha % des jours.
    """
    losses = -notional * returns
    return float(np.percentile(losses, alpha * 100))


def stress_loss(returns, shock, notional):
    """Nous calculons la perte dans un scénario de crise.

    Ici, le scénario est un choc direct sur le portefeuille : une baisse de `shock` (20 % par défaut).
    Pour 1 M$ et un choc de 20 %, cela donne 200 000 $. Les rendements simulés ne servent pas
    à ce calcul : un stress test ne dépend pas de ce que l'on a observé, c'est un scénario imposé.
    """
    return notional * shock


# Nous mettons les simulations en cache : si vous ne changez pas les paramètres,
# l'application ne recalcule rien et reste instantanée.
@st.cache_data
def get_returns(mu, sigma, days, seed):
    return simulate_returns(mu, sigma, days, seed)


def fmt(x):
    """Format simple pour les montants : 13 945 $."""
    x = 0.0 if round(x) == 0 else x        # évite l'affichage "-0 $"
    return f"{x:,.0f} $".replace(",", " ")


def fm(x):
    """Même format, mais avec le $ protégé : sans cela, Markdown prend deux $ pour une formule mathématique."""
    return fmt(x).replace("$", "\\$")


# ------------------------------------------------------------------
# 2. La page et ses réglages
# ------------------------------------------------------------------
st.set_page_config(page_title="Risque : VaR et stress test", layout="wide")
st.title("Combien pourriez-vous perdre ?")
st.caption("Un portefeuille de 1 M$, vu sous deux angles : une mauvaise journée et une crise.")

# La barre latérale contient les réglages. Vous pouvez les modifier : tout se met à jour tout de suite.
with st.sidebar:
    st.header("Réglages")
    conf = st.slider("Niveau de confiance (%)", 90, 99, 95,
                     help="Plus ce niveau est élevé, plus la VaR regarde loin dans les mauvais cas.")
    sigma = st.slider("Volatilité quotidienne (%)", 0.0, 5.0, 1.0, 0.1,
                      help="L'amplitude habituelle des variations d'un jour à l'autre. À 0 %, plus rien ne bouge.") / 100
    shock = st.slider("Choc du stress test (%)", 5, 50, 20,
                      help="La baisse imposée au portefeuille dans le scénario de crise (20 % pour un style Bâle III).") / 100
    notional = st.number_input("Taille du portefeuille ($)", 100_000, 100_000_000, 1_000_000, 100_000)

    if "seed" not in st.session_state:
        st.session_state.seed = 42
    if st.button("Nouvelle simulation"):
        st.session_state.seed += 1       # une nouvelle graine donne un nouvel historique
    st.caption("Hypothèses : 252 jours de rendements simulés, loi normale, rendement moyen nul.")

# ------------------------------------------------------------------
# 3. Les calculs
# ------------------------------------------------------------------
returns = get_returns(0.0, sigma, 252, st.session_state.seed)
losses = -notional * returns
var = calc_var(returns, conf / 100, notional)
stress = stress_loss(returns, shock, notional)
worst_day = float(losses.max())                       # la pire journée de notre historique
# Pour comparaison : la VaR théorique si les rendements suivent exactement une loi normale
var_theo = notional * sigma * NormalDist().inv_cdf(conf / 100)

# ------------------------------------------------------------------
# 4. Les chiffres clés
# ------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric(f"VaR à {conf} % (1 jour)", fmt(var))
c2.metric("Pire jour de l'historique", fmt(worst_day))
c3.metric(f"Scénario de crise (-{shock:.0%})", fmt(stress))

# ------------------------------------------------------------------
# 5. Les graphiques
# ------------------------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("Distribution des pertes journalières")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(losses, bins=30, color="#2F6DB5", alpha=0.85, label="Pertes journalières")
    ax.axvline(var, color="red", lw=2, label=f"VaR {conf} % : {fmt(var)}")
    ax.set_xlabel("Perte ($)  |  à gauche, vous gagnez ; à droite, vous perdez")
    ax.set_ylabel("Nombre de jours")
    ax.legend()
    ax.grid(alpha=0.3)
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Chaque barre compte les jours dont la perte tombe dans une même tranche. "
               "La ligne rouge marque le seuil que la perte dépasse seulement dans "
               f"{100 - conf} % des jours.")

with right:
    st.subheader("Mauvaise journée ou crise ?")
    fig2, ax2 = plt.subplots(figsize=(5, 4))
    ax2.bar(["VaR", "Pire jour", "Crise"], [var, worst_day, stress],
            color=["#2F6DB5", "#888888", "#C0392B"])
    ax2.set_ylabel("Perte ($)")
    ax2.grid(axis="y", alpha=0.3)
    st.pyplot(fig2)
    plt.close(fig2)
    st.caption("La crise est un scénario imposé, pas une prévision : il sert à vérifier que vous restez solide.")

# ------------------------------------------------------------------
# 6. Le résumé destiné au client
# ------------------------------------------------------------------
st.subheader("En résumé pour vous")
if var <= 0:
    # Cas limite : avec une volatilité nulle, rien ne bouge, donc la VaR est nulle.
    st.info("Avec une volatilité de 0 %, le portefeuille ne bouge pas : la VaR est nulle. "
            f"Seul le scénario de crise reste chiffré : {fm(stress)}.")
else:
    st.success(
        f"**{conf} % de sécurité à {fm(var)}, et une crise chiffrée à {fm(stress)}.**\n\n"
        f"- Sur une journée ordinaire, dans {conf} % des cas, votre perte devrait rester sous **{fm(var)}**.\n"
        f"- Dans une crise de type 2008 (baisse de {shock:.0%}), la perte monterait à **{fm(stress)}**, "
        f"soit environ **{stress / var:.0f} fois** la VaR.\n"
        f"- Ces deux chiffres répondent à deux questions différentes : l'un décrit une mauvaise journée, l'autre une catastrophe."
    )

with st.expander("Comment lire ces chiffres, et leurs limites"):
    st.markdown(
        f"""
**Comment la VaR est calculée.** Nous classons les 252 pertes simulées de la plus petite à la plus grande, puis nous prenons le seuil
au rang {conf} %. C'est la méthode de la simulation historique.

**Vérification.** Si les rendements suivent exactement une loi normale, la VaR théorique vaut **{fm(var_theo)}**.
Notre valeur ({fm(var)}) s'en approche, mais elle varie un peu d'une simulation à l'autre car nous n'avons que 252 jours.

**Limites à garder en tête :**
- la VaR ne dit rien de ce qui se passe *au-delà* du seuil : une perte peut être bien plus grande les {100 - conf} % restants ;
- nos rendements sont simulés avec une loi normale, alors que les vrais marchés ont des queues plus épaisses ;
- le stress test est un scénario choisi, pas une probabilité.
"""
    )
