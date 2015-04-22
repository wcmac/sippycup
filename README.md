<table>
<tr>

<td>
<img src="img/sippycup-small.jpg" align="left" style="padding-right: 30px"/>
</td>

<td>
<h1 style="line-height: 125%">SippyCup</h1>
<p>
  <a href="http://nlp.stanford.edu/~wcmac/">Bill MacCartney</a><br/>
  Spring 2015
</p>
</td>

</tr>
</table>

SippyCup is a simple semantic parser, written in Python, created purely for didactic purposes. The design favors simplicity and readability over efficiency and performance.  The goal is to make semantic parsing look easy!

SippyCup demonstrates an approach to semantic parsing based around:
- a context-free grammar with semantic attachments,
- a chart-parsing algorithm,
- a linear, feature-based scoring function for ranking candidate parses,
- learning of scoring parameters using stochastic gradient descent, and
- limited forms of grammar induction.

We present applications of SippyCup to three different domains:
- natural language arithmetic: "two times three plus four"
- travel queries: "driving directions to williamsburg virginia"
- geographical queries: "how many states border the largest state"

SippyCup was inspired by, and partly adapted from, the [demonstration code][] published as a companion to [Liang & Potts 2015][], "Bringing machine learning and compositional semantics together".  It was developed primarily for the benefit of students in Stanford's [CS224U: Natural Language Understanding], and therefore contains exercises (without solutions) for use in the class.  However, it should be of use to anyone interested in learning about semantic parsing.  If you're new to Python, you might find this [Python tutorial][] useful.

In addition to the Python source code, SippyCup includes a [codelab][] on semantic parsing,
published as a sequence of four [IPython Notebooks][]:
- [Unit 0][]: Introduction to semantic parsing
- [Unit 1][]: Natural language arithmetic
- [Unit 2][]: Travel queries
- [Unit 3][]: Geography queries

SippyCup remains a work in progress, and you will find a number of TODOs throughout this notebook and the accompanying Python codebase.  You will likely also find errors!  You can help to contribute to SippyCup by sending corrections to [the author](mailto:wcmac@cs.stanford.edu) or by sending a pull request to the SippyCup [GitHub repository][].

  [codelab]: http://nbviewer.ipython.org/github/wcmac/sippycup/blob/master/sippycup-unit-0.ipynb
  [Unit 0]: http://nbviewer.ipython.org/github/wcmac/sippycup/blob/master/sippycup-unit-0.ipynb
  [Unit 1]: http://nbviewer.ipython.org/github/wcmac/sippycup/blob/master/sippycup-unit-1.ipynb
  [Unit 2]: http://nbviewer.ipython.org/github/wcmac/sippycup/blob/master/sippycup-unit-2.ipynb
  [Unit 3]: http://nbviewer.ipython.org/github/wcmac/sippycup/blob/master/sippycup-unit-3.ipynb
  [IPython Notebooks]: http://ipython.org/notebook.html
  [Python tutorial]: http://cs231n.github.io/python-numpy-tutorial/
  [demonstration code]: https://github.com/cgpotts/annualreview-complearning
  [Liang & Potts 2015]: http://www.annualreviews.org/doi/pdf/10.1146/annurev-linguist-030514-125312
  [CS224U: Natural Language Understanding]: http://www.stanford.edu/class/cs224u/
  [GitHub repository]: https://github.com/wcmac/sippycup
