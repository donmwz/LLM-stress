import asyncio
import time
from typing import List

import httpx

from config import TestConfig, RequestResult, RequestStatus
from providers import get_provider, BaseProvider
from tokenizer import count_tokens


class AsyncEngine:
    def __init__(self, config: TestConfig):
        self.config = config
        self.provider: BaseProvider = get_provider(
            config.provider, config.api_key, config.model
        )
        self._semaphore = asyncio.Semaphore(config.concurrency)
        self.wall_clock_seconds: float = 0.0  # run() sonrası doldurulur (FAZ 2 - TPS için)
        self.run_start_perf: float = 0.0      # run() başlangıcının perf_counter değeri (FAZ 3 - zaman çizelgesi için)

    async def _send_single_request(
        self, client: httpx.AsyncClient, request_id: int
    ) -> RequestResult:
        async with self._semaphore:
            result = RequestResult(request_id=request_id, t0=time.perf_counter())
            prompt = (
                self.config.prompts[request_id % len(self.config.prompts)]
                if self.config.prompts
                else self.config.prompt
            )
            url, headers, body = self.provider.build_request(
                prompt, stream=self.config.stream
            )
            try:
                if self.config.stream:
                    await self._handle_streaming(client, url, headers, body, result)
                else:
                    await self._handle_non_streaming(client, url, headers, body, result)
            except httpx.TimeoutException:
                result.status = RequestStatus.TIMEOUT
                result.error_message = "İstek zaman aşımına uğradı"
                result.t2 = time.perf_counter()
            except Exception as e:
                result.status = RequestStatus.ERROR
                result.error_message = str(e)
                result.t2 = time.perf_counter()
            return result

    async def _handle_streaming(self, client, url, headers, body, result: RequestResult):
        async with client.stream(
            "POST", url, headers=headers, json=body, timeout=self.config.timeout
        ) as response:
            result.status_code = response.status_code

            if response.status_code == 429:
                result.status = RequestStatus.RATE_LIMITED
                result.t2 = time.perf_counter()
                return
            if response.status_code >= 400:
                error_body = await response.aread()
                result.status = RequestStatus.ERROR
                result.error_message = f"HTTP {response.status_code}: {error_body[:200]}"
                result.t2 = time.perf_counter()
                return

            collected = []
            got_first_token = False
            async for raw_line in response.aiter_lines():
                if not raw_line:
                    continue
                line_bytes = raw_line.encode("utf-8", errors="ignore")
                delta = self.provider.parse_stream_line(line_bytes)
                if delta:
                    if not got_first_token:
                        result.t1 = time.perf_counter()
                        got_first_token = True
                    collected.append(delta)

            result.t2 = time.perf_counter()
            full_text = "".join(collected)
            # Streaming yanıtlarda sağlayıcılar genelde kesin usage bilgisini
            # ayrı bir olayda/parametreyle döner; burada tiktoken ile YAKLAŞIK sayım kullanılıyor.
            result.token_count = count_tokens(full_text)
            if self.config.save_responses:
                result.output_text = full_text
            result.status = RequestStatus.SUCCESS

    async def _handle_non_streaming(self, client, url, headers, body, result: RequestResult):
        response = await client.post(
            url, headers=headers, json=body, timeout=self.config.timeout
        )
        result.status_code = response.status_code
        result.t2 = time.perf_counter()
        result.t1 = result.t2  # streaming yok, TTFT = toplam süre

        if response.status_code == 429:
            result.status = RequestStatus.RATE_LIMITED
            return
        if response.status_code >= 400:
            result.status = RequestStatus.ERROR
            result.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
            return

        data = response.json()
        text = self.provider.parse_full_response(data)
        # Önce sağlayıcının bildirdiği KESİN token sayısını dene, yoksa yaklaşık say.
        exact_tokens = self.provider.extract_completion_tokens(data)
        result.token_count = exact_tokens if exact_tokens is not None else count_tokens(text)
        if self.config.save_responses:
            result.output_text = text
        result.status = RequestStatus.SUCCESS

    async def run(self) -> List[RequestResult]:
        """
        Tüm test koşusunu çalıştırır.
        ramp_up=True ise istekler ramp_up_delay aralıklarla kademeli başlatılır;
        aksi halde hepsi anında (concurrency limitine kadar paralel) fırlatılır.
        """
        limits = httpx.Limits(
            max_connections=self.config.concurrency,
            max_keepalive_connections=self.config.concurrency,
        )
        run_start = time.perf_counter()
        self.run_start_perf = run_start
        async with httpx.AsyncClient(limits=limits) as client:
            tasks = []
            for i in range(self.config.total_requests):
                if self.config.ramp_up and i > 0:
                    await asyncio.sleep(self.config.ramp_up_delay)
                tasks.append(asyncio.create_task(self._send_single_request(client, i)))
            results = await asyncio.gather(*tasks)
        self.wall_clock_seconds = time.perf_counter() - run_start
        return list(results)
