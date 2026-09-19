# Настройка видеозадач в cron-job.org

Встроенное расписание GitHub Actions не используется. Две независимые задачи
cron-job.org вызывают один workflow с разными видеослотами.

Общие параметры обеих задач:

- Method: `POST`
- URL: `https://api.github.com/repos/teadrunkerhard777/MMA-autoposter/actions/workflows/video-post.yml/dispatches`
- Header `Accept`: `application/vnd.github+json`
- Header `Authorization`: `Bearer YOUR_FINE_GRAINED_TOKEN`
- Header `X-GitHub-Api-Version`: `2026-03-10`
- Header `Content-Type`: `application/json`
- Timezone: `Asia/Yekaterinburg`
- Request timeout: `30 seconds`
- Automatic retries: `Off`

Токен должен иметь доступ только к `MMA-autoposter` и разрешение
**Actions: Read and write**. Храните его только в приватном заголовке задачи.

## Дневной ролик

- Title: `MMA Video Day`
- Schedule: `0 13 * * *`
- Body: `{"ref":"main","inputs":{"slot":"day","publish":true}}`

## Вечерний ролик

- Title: `MMA Video Evening`
- Schedule: `0 20 * * *`
- Body: `{"ref":"main","inputs":{"slot":"evening","publish":true}}`

Успешный запрос возвращает HTTP 204. После сохранения сначала запустите каждую
задачу вручную и убедитесь, что появился соответствующий запуск `MMA TODAY
Video Post`. Повторные запросы отключены, чтобы неопределённый сетевой результат
не породил второй запуск.
