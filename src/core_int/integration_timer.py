# Copyright (c) 2020, Digital Asset (Switzerland) GmbH and/or its affiliates.
# SPDX-License-Identifier: Apache-2.0

import asyncio

from dataclasses import dataclass

from dazl import exercise

from daml_dit_if.api import \
    IntegrationEnvironment, \
    IntegrationEvents, \
    getIntegrationLogger


LOG = getIntegrationLogger()


@dataclass
class IntegrationTimerEnv(IntegrationEnvironment):
    interval: int
    targetTemplate: str
    templateChoice: str
    batchSize: int


def batch_commands(commands, batch_size):
    return list(commands[ii:ii+batch_size] for ii in range(0, len(commands), batch_size))


def integration_timer_main(
        env: 'IntegrationTimerEnv',
        events: 'IntegrationEvents'):

    active_cids = set()

    @events.ledger.contract_created(env.targetTemplate)
    async def on_contract_created(event):
        LOG.debug('Created CID: %r', event.cid)
        active_cids.add(event.cid)

    @events.ledger.contract_archived(env.targetTemplate)
    async def on_ledger_archived(event):
        LOG.debug('Archived CID: %r', event.cid)
        active_cids.discard(event.cid)

    @events.time.periodic_interval(env.interval, label='Periodic Timer')
    async def interval_timer_elapsed():
        LOG.debug('Timer elapsed: %r', active_cids)
        commands = [exercise(cid, env.templateChoice, {})
                    for cid
                    in active_cids]

        for batch in batch_commands(commands, env.batchSize):
            await env.queue.put(batch)

    @events.queue.message()
    async def handle_command_batch(message):
        LOG.debug('Submitting command batch, n=%r', len(message))
        return message

