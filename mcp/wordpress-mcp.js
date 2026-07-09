import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const WP_URL = (process.env.WP_URL || 'http://localhost:8080').replace(/\/$/, '');
const WP_USERNAME = process.env.WP_USERNAME || 'admin';
const WP_APP_PASSWORD = process.env.WP_APP_PASSWORD || '';

const AUTH_HEADER = 'Basic ' + Buffer.from(`${WP_USERNAME}:${WP_APP_PASSWORD}`).toString('base64');

async function wpFetch(path, method = 'GET', body = null) {
  const url = path.startsWith('http') ? path : `${WP_URL}/wp-json/wp/v2${path}`;
  const opts = {
    method,
    headers: { Authorization: AUTH_HEADER, 'Content-Type': 'application/json' },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`WordPress API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

const TOOLS = [
  {
    name: 'wp_get_site_info',
    description: 'Get WordPress site name, URL, description, and version',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'wp_list_posts',
    description: 'List WordPress posts with optional filters',
    inputSchema: {
      type: 'object',
      properties: {
        status: {
          type: 'string',
          description: 'Post status: draft | publish | pending | private (default: draft)',
        },
        per_page: { type: 'number', description: 'Results per page, max 100 (default: 10)' },
        search: { type: 'string', description: 'Keyword search' },
        categories: { type: 'string', description: 'Comma-separated category IDs' },
      },
    },
  },
  {
    name: 'wp_get_post',
    description: 'Get a WordPress post by ID',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'number', description: 'Post ID' },
      },
      required: ['id'],
    },
  },
  {
    name: 'wp_create_post',
    description: 'Create a new WordPress post (defaults to draft)',
    inputSchema: {
      type: 'object',
      properties: {
        title: { type: 'string', description: 'Post title' },
        content: { type: 'string', description: 'Post content as HTML' },
        status: { type: 'string', description: 'draft | publish | pending (default: draft)' },
        excerpt: { type: 'string', description: 'Post excerpt' },
        categories: {
          type: 'array',
          items: { type: 'number' },
          description: 'Array of category IDs',
        },
        tags: {
          type: 'array',
          items: { type: 'number' },
          description: 'Array of tag IDs',
        },
      },
      required: ['title', 'content'],
    },
  },
  {
    name: 'wp_update_post',
    description: 'Update an existing WordPress post by ID',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'number', description: 'Post ID to update' },
        title: { type: 'string', description: 'New title' },
        content: { type: 'string', description: 'New content as HTML' },
        status: { type: 'string', description: 'New status: draft | publish | pending' },
        categories: { type: 'array', items: { type: 'number' } },
        tags: { type: 'array', items: { type: 'number' } },
      },
      required: ['id'],
    },
  },
  {
    name: 'wp_delete_post',
    description: 'Move a WordPress post to trash (set force=true to permanently delete)',
    inputSchema: {
      type: 'object',
      properties: {
        id: { type: 'number', description: 'Post ID to delete' },
        force: { type: 'boolean', description: 'Permanently delete without trash (default: false)' },
      },
      required: ['id'],
    },
  },
  {
    name: 'wp_list_categories',
    description: 'List all WordPress categories',
    inputSchema: {
      type: 'object',
      properties: {
        per_page: { type: 'number', description: 'Results per page (default: 100)' },
        search: { type: 'string', description: 'Keyword search' },
      },
    },
  },
  {
    name: 'wp_list_tags',
    description: 'List WordPress tags with optional keyword search',
    inputSchema: {
      type: 'object',
      properties: {
        per_page: { type: 'number', description: 'Results per page (default: 100)' },
        search: { type: 'string', description: 'Keyword search' },
      },
    },
  },
  {
    name: 'wp_create_category',
    description: 'Create a new WordPress category',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Category name' },
        slug: { type: 'string', description: 'URL-friendly slug' },
        description: { type: 'string', description: 'Category description' },
        parent: { type: 'number', description: 'Parent category ID (0 = top-level)' },
      },
      required: ['name'],
    },
  },
  {
    name: 'wp_create_tag',
    description: 'Create a new WordPress tag',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Tag name' },
        slug: { type: 'string', description: 'URL-friendly slug' },
        description: { type: 'string', description: 'Tag description' },
      },
      required: ['name'],
    },
  },
];

const server = new Server(
  { name: 'wordpress-mcp', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args = {} } = req.params;

  try {
    let result;

    switch (name) {
      case 'wp_get_site_info': {
        result = await fetch(`${WP_URL}/wp-json/`, {
          headers: { Authorization: AUTH_HEADER },
        }).then((r) => r.json());
        result = {
          name: result.name,
          description: result.description,
          url: result.url,
          home: result.home,
          gmt_offset: result.gmt_offset,
          timezone_string: result.timezone_string,
        };
        break;
      }

      case 'wp_list_posts': {
        const q = new URLSearchParams();
        q.set('status', args.status || 'draft');
        q.set('per_page', String(Math.min(Number(args.per_page) || 10, 100)));
        if (args.search) q.set('search', args.search);
        if (args.categories) q.set('categories', args.categories);
        const posts = await wpFetch(`/posts?${q}`);
        result = posts.map((p) => ({
          id: p.id,
          title: p.title?.rendered,
          status: p.status,
          date: p.date,
          link: p.link,
          categories: p.categories,
          tags: p.tags,
        }));
        break;
      }

      case 'wp_get_post': {
        const p = await wpFetch(`/posts/${args.id}`);
        result = {
          id: p.id,
          title: p.title?.rendered,
          content: p.content?.rendered,
          excerpt: p.excerpt?.rendered,
          status: p.status,
          date: p.date,
          link: p.link,
          categories: p.categories,
          tags: p.tags,
        };
        break;
      }

      case 'wp_create_post': {
        const body = {
          title: args.title,
          content: args.content,
          status: args.status || 'draft',
        };
        if (args.excerpt) body.excerpt = args.excerpt;
        if (args.categories) body.categories = args.categories;
        if (args.tags) body.tags = args.tags;
        const p = await wpFetch('/posts', 'POST', body);
        result = { id: p.id, title: p.title?.rendered, status: p.status, link: p.link };
        break;
      }

      case 'wp_update_post': {
        const body = {};
        if (args.title !== undefined) body.title = args.title;
        if (args.content !== undefined) body.content = args.content;
        if (args.status !== undefined) body.status = args.status;
        if (args.categories !== undefined) body.categories = args.categories;
        if (args.tags !== undefined) body.tags = args.tags;
        const p = await wpFetch(`/posts/${args.id}`, 'POST', body);
        result = { id: p.id, title: p.title?.rendered, status: p.status, link: p.link };
        break;
      }

      case 'wp_delete_post': {
        const qs = args.force ? '?force=true' : '';
        result = await wpFetch(`/posts/${args.id}${qs}`, 'DELETE');
        break;
      }

      case 'wp_list_categories': {
        const q = new URLSearchParams();
        q.set('per_page', String(Math.min(Number(args.per_page) || 100, 100)));
        if (args.search) q.set('search', args.search);
        const cats = await wpFetch(`/categories?${q}`);
        result = cats.map((c) => ({ id: c.id, name: c.name, slug: c.slug, count: c.count }));
        break;
      }

      case 'wp_list_tags': {
        const q = new URLSearchParams();
        q.set('per_page', String(Math.min(Number(args.per_page) || 100, 100)));
        if (args.search) q.set('search', args.search);
        const tags = await wpFetch(`/tags?${q}`);
        result = tags.map((t) => ({ id: t.id, name: t.name, slug: t.slug, count: t.count }));
        break;
      }

      case 'wp_create_category': {
        const body = { name: args.name };
        if (args.slug) body.slug = args.slug;
        if (args.description) body.description = args.description;
        if (args.parent !== undefined) body.parent = args.parent;
        const cat = await wpFetch('/categories', 'POST', body);
        result = { id: cat.id, name: cat.name, slug: cat.slug };
        break;
      }

      case 'wp_create_tag': {
        const body = { name: args.name };
        if (args.slug) body.slug = args.slug;
        if (args.description) body.description = args.description;
        const tag = await wpFetch('/tags', 'POST', body);
        result = { id: tag.id, name: tag.name, slug: tag.slug };
        break;
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return {
      content: [{ type: 'text', text: `Error: ${err.message}` }],
      isError: true,
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
