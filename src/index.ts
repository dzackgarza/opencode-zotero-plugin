import { type Plugin, tool } from '@opencode-ai/plugin';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const PYTHON_COMMAND_TIMEOUT_MS = 90000;

async function callZotero(
  toolName: string,
  args: Record<string, unknown>,
): Promise<string> {
  try {
    const cliGitRepo = 'git+file:///home/dzack/opencode-plugins/zotero-manager';
    const { stdout } = await execFileAsync(
      'uvx',
      [
        '--from',
        cliGitRepo,
        'python',
        '-m',
        'zotero_librarian._dispatch',
        toolName,
        JSON.stringify(args),
      ],
      {
        timeout: PYTHON_COMMAND_TIMEOUT_MS,
      },
    );
    return stdout.trim();
  } catch (error) {
    const failed = error as { stdout?: string; stderr?: string; message: string };
    const stdout = failed.stdout?.trim();
    const stderr = failed.stderr?.trim();
    if (stdout) {
      return stdout;
    }
    return JSON.stringify({
      success: false,
      operation: toolName,
      stage: 'plugin_process',
      error: stderr || failed.message,
    });
  }
}

export const ZoteroPlugin: Plugin = async () => ({
  tool: {
    zotero_count: tool({
      description:
        'Use when you only need the total number of items in the Zotero library.',
      args: {},
      async execute() {
        return callZotero('count_items', {});
      },
    }),
    zotero_stats: tool({
      description:
        'Use when you need aggregate library statistics such as summary, item types, years, tags, or attachment counts.',
      args: {
        action: tool.schema
          .string()
          .describe("'summary', 'types', 'years', 'tags', or 'attachments'"),
      },
      async execute(args) {
        if (args.action === 'types') return callZotero('items_per_type', {});
        if (args.action === 'years') return callZotero('items_per_year', {});
        if (args.action === 'tags') return callZotero('tag_cloud', {});
        if (args.action === 'attachments') return callZotero('attachment_summary', {});
        return callZotero('library_summary', {});
      },
    }),
    zotero_search: tool({
      description: 'Use when you need to search or filter the local Zotero library.',
      args: {
        action: tool.schema.string().describe('Search action'),
        query: tool.schema
          .string()
          .optional()
          .describe('Search query for title, author, or DOI lookups'),
      },
      async execute(args) {
        if (args.action === 'by_title')
          return callZotero('search_by_title', { query: args.query || '' });
        if (args.action === 'by_author')
          return callZotero('search_by_author', { name: args.query || '' });
        if (args.action === 'without_pdf') return callZotero('items_without_pdf', {});
        if (args.action === 'without_tags') return callZotero('items_without_tags', {});
        if (args.action === 'not_in_collection')
          return callZotero('items_not_in_collection', {});
        if (args.action === 'duplicate_dois') return callZotero('duplicate_dois', {});
        if (args.action === 'duplicate_titles')
          return callZotero('duplicate_titles', {});
        if (args.action === 'invalid_dois')
          return callZotero('items_with_invalid_doi', {});
        if (args.action === 'by_doi')
          return callZotero('get_item_by_doi', { doi: args.query || '' });
        return JSON.stringify({ error: `Unknown action: ${args.action}` });
      },
    }),
    zotero_get_item: tool({
      description: 'Use when you need the full Zotero record for a specific item key.',
      args: {
        item_key: tool.schema.string().describe('Zotero item key'),
      },
      async execute(args) {
        return callZotero('get_item', { item_key: args.item_key });
      },
    }),
    zotero_children: tool({
      description: 'Use when you need attachments or notes for a Zotero item.',
      args: {
        item_key: tool.schema.string().describe('Parent Zotero item key'),
      },
      async execute(args) {
        return callZotero('get_children', { item_key: args.item_key });
      },
    }),
    zotero_update_item: tool({
      description: 'Use when you need to update fields on an existing Zotero item.',
      args: {
        item_key: tool.schema.string().describe('Zotero item key'),
        fields: tool.schema
          .record(tool.schema.string(), tool.schema.any())
          .describe('Fields to update'),
      },
      async execute(args) {
        return callZotero('update_item_fields', {
          item_key: args.item_key,
          fields: args.fields,
        });
      },
    }),
    zotero_tags: tool({
      description: 'Use when you need to inspect or edit Zotero item tags.',
      args: {
        action: tool.schema.string().describe("'list', 'add', or 'remove'"),
        item_key: tool.schema
          .string()
          .optional()
          .describe('Item key for add/remove operations'),
        tags: tool.schema
          .array(tool.schema.string())
          .optional()
          .describe('Tags to add or remove'),
      },
      async execute(args) {
        if (args.action === 'list') return callZotero('all_tags', {});
        if (args.action === 'add')
          return callZotero('add_tags_to_item', {
            item_key: args.item_key,
            tags: args.tags,
          });
        if (args.action === 'remove')
          return callZotero('remove_tags_from_item', {
            item_key: args.item_key,
            tags: args.tags,
          });
        return JSON.stringify({ error: `Unknown action: ${args.action}` });
      },
    }),
    zotero_import: tool({
      description: 'Use when you need to import a DOI, ISBN, or PMID into Zotero.',
      args: {
        action: tool.schema.string().describe("'by_doi', 'by_isbn', or 'by_pmid'"),
        identifier: tool.schema.string().describe('Identifier to import'),
      },
      async execute(args) {
        if (args.action === 'by_doi')
          return callZotero('import_by_doi', { doi: args.identifier });
        if (args.action === 'by_isbn')
          return callZotero('import_by_isbn', { isbn: args.identifier });
        if (args.action === 'by_pmid')
          return callZotero('import_by_pmid', { pmid: args.identifier });
        return JSON.stringify({ error: `Unknown action: ${args.action}` });
      },
    }),
    zotero_batch_add: tool({
      description: 'Use when you need to import many identifiers into Zotero at once.',
      args: {
        identifiers: tool.schema
          .array(tool.schema.string())
          .describe('Identifiers to import in order'),
        id_type: tool.schema.string().optional().describe("'doi', 'isbn', or 'pmid'"),
        collection: tool.schema
          .string()
          .optional()
          .describe('Collection key to add imported items into'),
        tags: tool.schema
          .string()
          .optional()
          .describe('Comma-separated tags to add to imported items'),
        force: tool.schema.boolean().optional().describe('Skip duplicate detection'),
      },
      async execute(args) {
        return callZotero('batch_add_identifiers', args);
      },
    }),
    zotero_export: tool({
      description: 'Use when you need a text export of the Zotero library.',
      args: {
        action: tool.schema
          .string()
          .describe("'json', 'bibtex', 'csv', 'ris', or 'csljson'"),
        collection: tool.schema
          .string()
          .optional()
          .describe('Optional collection key filter'),
      },
      async execute(args) {
        if (args.collection && ['json', 'bibtex', 'csv'].includes(args.action)) {
          return callZotero('export_collection', {
            collection_key: args.collection,
            format: args.action,
          });
        }
        if (args.action === 'json') return callZotero('export_to_json', {});
        if (args.action === 'bibtex') return callZotero('export_to_bibtex', {});
        if (args.action === 'csv') return callZotero('export_to_csv', {});
        if (args.action === 'ris')
          return callZotero('export_to_ris', { collection: args.collection });
        if (args.action === 'csljson')
          return callZotero('export_to_csljson', { collection: args.collection });
        return JSON.stringify({ error: `Unknown action: ${args.action}` });
      },
    }),
    zotero_collections: tool({
      description: 'Use when you need to inspect collections or move an item into one.',
      args: {
        action: tool.schema.string().describe("'list' or 'move_item'"),
        item_key: tool.schema.string().optional().describe('Item key'),
        collection_key: tool.schema.string().optional().describe('Collection key'),
      },
      async execute(args) {
        if (args.action === 'list') return callZotero('get_collections', {});
        if (args.action === 'move_item')
          return callZotero('move_item_to_collection', {
            item_key: args.item_key,
            collection_key: args.collection_key,
          });
        return JSON.stringify({ error: `Unknown action: ${args.action}` });
      },
    }),
    zotero_delete_items: tool({
      description: 'Use when you need to move one or more Zotero items to trash.',
      args: {
        item_keys: tool.schema
          .array(tool.schema.string())
          .describe('Item keys to move to trash'),
      },
      async execute(args) {
        if (args.item_keys.length === 1)
          return callZotero('delete_item', { item_key: args.item_keys[0] });
        return callZotero('delete_items', { item_keys: args.item_keys });
      },
    }),
    zotero_check_pdfs: tool({
      description:
        'Use when you need a summary of which Zotero items are missing PDFs.',
      args: {
        collection: tool.schema
          .string()
          .optional()
          .describe('Optional collection key filter'),
      },
      async execute(args) {
        return callZotero('check_pdfs', args);
      },
    }),
    zotero_crossref: tool({
      description:
        'Use when you need to match citation text against the local Zotero library.',
      args: {
        text: tool.schema.string().describe('Citation text in Author (Year) form'),
        collection: tool.schema
          .string()
          .optional()
          .describe('Optional collection key filter'),
      },
      async execute(args) {
        return callZotero('crossref_citations', args);
      },
    }),
    zotero_find_dois: tool({
      description:
        'Use when you need CrossRef-powered DOI backfilling for local Zotero items.',
      args: {
        apply: tool.schema
          .boolean()
          .optional()
          .describe('Write matched DOIs back to Zotero'),
        limit: tool.schema.number().optional().describe('Maximum items to process'),
        collection: tool.schema.string().optional().describe('Collection key filter'),
      },
      async execute(args) {
        return callZotero('find_missing_dois', args);
      },
    }),
    zotero_fetch_pdfs: tool({
      description:
        'Use when you need to discover or attach open-access PDFs for Zotero items.',
      args: {
        dry_run: tool.schema
          .boolean()
          .optional()
          .describe('Show matches without downloading'),
        limit: tool.schema.number().optional().describe('Maximum items to process'),
        collection: tool.schema.string().optional().describe('Collection key filter'),
        download_dir: tool.schema
          .string()
          .optional()
          .describe('Directory to save PDFs into'),
        upload: tool.schema
          .boolean()
          .optional()
          .describe('Upload fetched PDFs to Zotero storage'),
        sources: tool.schema
          .array(tool.schema.string())
          .optional()
          .describe('PDF sources to try in order'),
      },
      async execute(args) {
        return callZotero('fetch_pdfs', args);
      },
    }),
  },
});
