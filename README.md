# 凛スケジュールTwitterBotプログラム

## 仕様
- [凛のホームページ](http://www.rinkikurin.com/)の[予約ページ](http://www.rinkikurin.com/%E3%81%94%E4%BA%88%E7%B4%84)を解析し、予約状況をつぶやく。
- 18：30まではその日の予定をつぶやく。過ぎた場合は翌日の予定をつぶやく。
 - 翌日がお休みの場合、 `xxxx年xx月xx日(曜日)は定休日です` とつぶやく。
 - 当日がお休みの場合、 `本日は定休日です` とつぶやく。
 - Twitterの仕様上、同一メッセージの連続投稿はできない
- 過ぎてしまった予定(ーのもの)は除外する。
- すべて予定が埋まっている場合、予約終了のメッセージをつぶやく

## 未確定
- xx:30の時間はTwitterの文字数の制限上スキップしているが、そこから1時間空いている場合どうするか。
- 夜間帯のTweetをしないようにするか(22時〜8時とか)
