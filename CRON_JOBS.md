# Настройка видеозадач в cron-job.org

Встроенное расписание GitHub Actions не используется. Одна задача cron-job.org
вызывает видеопостинг два раза в день. Workflow сам определяет дневной или
вечерний слот по времени `Asia/Yekaterinburg`.

Параметры задачи:

- Method: `POST`
- URL: `https://api.github.com/repos/teadrunkerhard777/MMA-autoposter/actions/workflows/video-post.yml/dispatches`
- Header `Accept`: `application/vnd.github+json`
- Header `Authorization`: `Bearer YOUR_FINE_GRAINED_TOKEN`
- Header `X-GitHub-Api-Version`: `2026-03-10`
- Header `Content-Type`: `application/json`
- Timezone: `Asia/Yekaterinburg`
- Title: `MMA Video Autoposter`
- Schedule: `0 13,20 * * *`
- Body: `{"ref":"main","inputs":{"publish":true}}`
- Request timeout: `30 seconds`
- Automatic retries: `Off`

Токен должен иметь доступ только к `MMA-autoposter` и разрешение
**Actions: Read and write**. Храните его только в приватном заголовке задачи.

Успешный запрос возвращает HTTP 204. После сохранения запустите задачу вручную
и убедитесь, что появился запуск `MMA TODAY Video Post`. Повторные запросы
отключены, чтобы неопределённый сетевой результат не породил второй запуск.
