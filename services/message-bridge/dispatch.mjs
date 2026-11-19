// Persist before side effects: an uncertain add must never become a second add.
export async function dispatch(request, journal, persist, rpc) {
  const threadId = request.thread_id;
  const submission = journal.submission_id || request.submission_id;
  const q = await rpc('thread/queue/list', {threadId});
  let entry = q.data.find(x => x.id === submission || x.clientUserMessageId === request.client_id);
  if (!entry && submission) return {state: 'consumed_pending_ack', submission_id: submission};
  if (!entry && journal.add_attempted) return {state: 'delivery_uncertain'};
  if (!entry) {
    journal.add_attempted = true;
    persist(journal);
    entry = (await rpc('thread/queue/add', {threadId, clientUserMessageId: request.client_id,
      input: [{type: 'text', text: request.message}]})).queuedSubmission;
  }
  journal.submission_id = entry.id;
  persist(journal);
  const result = {state: 'queued', submission_id: entry.id};
  try {
    await rpc('thread/resume', {threadId});
    await rpc('thread/queue/start', {threadId, queuedSubmissionId: entry.id});
    return {...result, state: 'started'};
  } catch (e) { return {...result, error: e.message}; }
}
