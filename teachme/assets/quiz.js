/* Composant quiz réutilisable — cours « RAG IIIe République ».
   Usage dans une leçon :
     <div class="quiz" data-answer="2">            <!-- index 1-based de la bonne option -->
       <p class="quiz-q">Question ?</p>
       <button class="quiz-opt">option A</button>
       <button class="quiz-opt">option B</button>  <!-- ← bonne réponse ici -->
       <p class="quiz-fb">Feedback montré après réponse.</p>
     </div>
   Contrainte de conception : toutes les options d'une même question ont le même
   nombre de mots (pas d'indice via la mise en forme). Feedback immédiat = boucle
   de rétroaction courte ; la réponse se verrouille après un clic (recall, pas reconnaissance). */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.quiz').forEach(function (q) {
    var answer = parseInt(q.dataset.answer, 10);
    var opts = q.querySelectorAll('.quiz-opt');
    opts.forEach(function (btn, idx) {
      btn.addEventListener('click', function () {
        if (q.classList.contains('answered')) return;
        q.classList.add('answered');
        var ok = (idx + 1 === answer);
        btn.classList.add(ok ? 'correct' : 'wrong');
        if (!ok) opts[answer - 1].classList.add('correct');
        opts.forEach(function (b) { b.disabled = true; });
      });
    });
  });
});
