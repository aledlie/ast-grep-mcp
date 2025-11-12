---
name: base-controller-pattern
description: TypeScript BaseController pattern for Express.js APIs with standardized response handling, error tracking, and type safety
triggers:
  keywords:
    - basecontroller
    - base controller
    - controller pattern
    - express controller
  intent_patterns:
    - "create.*controller"
    - "add.*controller"
    - "implement.*controller"
    - "controller.*pattern"
    - "standardized.*response"
  file_patterns:
    - "**/*Controller.ts"
    - "**/controllers/*.ts"
enforcement: suggest
---

# BaseController Pattern

A production-ready TypeScript pattern for Express.js controllers with standardized response handling, automatic error tracking, type safety, and consistent API responses.

## Overview

The BaseController pattern provides a base class that all controllers extend to ensure:
- **Consistent API responses** across all endpoints
- **Automatic Sentry error tracking** for all errors
- **Type-safe response handling** with TypeScript generics
- **Centralized logging** with structured logs
- **Validation error handling** with detailed error messages
- **Pagination support** with metadata

## Core Pattern

### BaseController Class

```typescript
import { Response } from 'express';
import { ApiResponse, ApiError } from '@/utils/response';
import { isAppError } from '@/utils/errors';
import { logger } from '@/utils/logger';
import { captureException } from '@/config/sentry.config';
import { unifiedConfig } from '@/config';

/**
 * BaseController
 *
 * CRITICAL PATTERN: All controllers MUST extend this class
 *
 * Provides standardized response handling and error handling for all controllers.
 * Ensures consistent API responses and proper error tracking via Sentry.
 */
export abstract class BaseController {
  /**
   * Handle successful responses
   * Sends a standardized success response with data
   */
  protected handleSuccess<T>(
    res: Response,
    data: T,
    message: string = 'Success',
    statusCode: number = 200
  ): Response {
    const response: ApiResponse<T> = {
      success: true,
      message,
      data,
      timestamp: new Date().toISOString(),
    };

    logger.info(`[${this.constructor.name}] Success response`, {
      message,
      statusCode,
    });

    return res.status(statusCode).json(response);
  }

  /**
   * Handle error responses
   * Sends a standardized error response and logs to Sentry
   *
   * IMPORTANT: ALL errors are automatically captured to Sentry
   */
  protected handleError(
    res: Response,
    error: Error,
    message: string = 'An error occurred',
    statusCode?: number
  ): Response {
    // Determine status code
    const finalStatusCode = statusCode || (isAppError(error) ? error.statusCode : 500);

    // Capture error to Sentry (MANDATORY: ALL errors MUST be captured)
    captureException(error, {
      controller: this.constructor.name,
      message,
      statusCode: finalStatusCode,
    });

    // Log error
    logger.error(`[${this.constructor.name}] Error occurred`, {
      message,
      error: error.message,
      stack: error.stack,
      statusCode: finalStatusCode,
    });

    // Create error response
    const errorResponse: ApiError = {
      success: false,
      message,
      error: error.message,
      timestamp: new Date().toISOString(),
      // Include stack trace only in development
      ...(unifiedConfig.isDevelopment && {
        stack: error.stack,
      }),
    };

    return res.status(finalStatusCode).json(errorResponse);
  }

  /**
   * Handle validation errors from Zod
   * Formats Zod validation errors into a user-friendly response
   */
  protected handleValidationError(res: Response, error: unknown): Response {
    let details = {};

    // Check if it's a Zod error
    if (
      typeof error === 'object' &&
      error !== null &&
      'issues' in error &&
      Array.isArray((error as { issues: unknown[] }).issues)
    ) {
      details = (error as { issues: { path: string[]; message: string }[] }).issues.reduce(
        (acc, issue) => {
          const path = issue.path.join('.');
          acc[path] = issue.message;
          return acc;
        },
        {} as Record<string, string>
      );
    }

    const errorResponse: ApiError = {
      success: false,
      message: 'Validation failed',
      error: 'Invalid request data',
      timestamp: new Date().toISOString(),
      details,
    };

    logger.warn(`[${this.constructor.name}] Validation error`, { details });

    return res.status(422).json(errorResponse);
  }

  /**
   * Handle paginated responses
   * Sends a standardized paginated response with metadata
   */
  protected handlePaginatedResponse<T>(
    res: Response,
    items: T[],
    page: number,
    limit: number,
    total: number,
    message: string = 'Success'
  ): Response {
    const totalPages = Math.ceil(total / limit);

    const response: ApiResponse<{ items: T[] }> = {
      success: true,
      message,
      data: { items },
      timestamp: new Date().toISOString(),
      meta: {
        page,
        limit,
        total,
        totalPages,
        hasNextPage: page < totalPages,
        hasPrevPage: page > 1,
      },
    };

    logger.info(`[${this.constructor.name}] Paginated response`, {
      page,
      limit,
      total,
      itemCount: items.length,
    });

    return res.status(200).json(response);
  }
}
```

## Usage Examples

### Basic Controller

```typescript
import { Request, Response } from 'express';
import { BaseController } from '@/controllers/BaseController';
import { AnalyticsService } from '@/services/AnalyticsService';

export class AnalyticsController extends BaseController {
  constructor(private analyticsService: AnalyticsService) {
    super();
  }

  /**
   * Track event endpoint
   * POST /api/events/track
   */
  async trackEvent(req: Request, res: Response): Promise<Response> {
    try {
      const event = await this.analyticsService.trackEvent(req.body);
      return this.handleSuccess(res, event, 'Event tracked successfully', 201);
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to track event');
    }
  }

  /**
   * Get analytics stats
   * GET /api/analytics/stats
   */
  async getStats(req: Request, res: Response): Promise<Response> {
    try {
      const stats = await this.analyticsService.getStats(req.query);
      return this.handleSuccess(res, stats);
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to retrieve stats');
    }
  }
}
```

### Controller with Validation

```typescript
export class ProjectController extends BaseController {
  async createProject(req: Request, res: Response): Promise<Response> {
    try {
      // Validate request body with Zod
      const validatedData = createProjectSchema.parse(req.body);

      const project = await this.projectService.create(validatedData);
      return this.handleSuccess(res, project, 'Project created', 201);
    } catch (error) {
      // Check if it's a Zod validation error
      if (error instanceof ZodError) {
        return this.handleValidationError(res, error);
      }
      return this.handleError(res, error as Error, 'Failed to create project');
    }
  }
}
```

### Controller with Pagination

```typescript
export class EventController extends BaseController {
  async listEvents(req: Request, res: Response): Promise<Response> {
    try {
      const page = parseInt(req.query.page as string) || 1;
      const limit = parseInt(req.query.limit as string) || 10;

      const { events, total } = await this.eventService.findAll({ page, limit });

      return this.handlePaginatedResponse(
        res,
        events,
        page,
        limit,
        total,
        'Events retrieved successfully'
      );
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to retrieve events');
    }
  }
}
```

## Response Formats

### Success Response

```json
{
  "success": true,
  "message": "Event tracked successfully",
  "data": {
    "id": "evt_123",
    "type": "page_view",
    "timestamp": "2025-11-11T10:00:00Z"
  },
  "timestamp": "2025-11-11T10:00:01Z"
}
```

### Error Response (Production)

```json
{
  "success": false,
  "message": "Failed to track event",
  "error": "Event validation failed",
  "timestamp": "2025-11-11T10:00:01Z"
}
```

### Error Response (Development)

```json
{
  "success": false,
  "message": "Failed to track event",
  "error": "Event validation failed",
  "timestamp": "2025-11-11T10:00:01Z",
  "stack": "Error: Event validation failed\n    at AnalyticsService.trackEvent..."
}
```

### Validation Error Response

```json
{
  "success": false,
  "message": "Validation failed",
  "error": "Invalid request data",
  "timestamp": "2025-11-11T10:00:01Z",
  "details": {
    "email": "Invalid email format",
    "age": "Must be a positive number"
  }
}
```

### Paginated Response

```json
{
  "success": true,
  "message": "Events retrieved successfully",
  "data": {
    "items": [
      { "id": "evt_1", "type": "page_view" },
      { "id": "evt_2", "type": "button_click" }
    ]
  },
  "timestamp": "2025-11-11T10:00:01Z",
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 42,
    "totalPages": 5,
    "hasNextPage": true,
    "hasPrevPage": false
  }
}
```

## TypeScript AST Structure

### Abstract Class Declaration

**AST Pattern**:
```
export_statement
  abstract_class_declaration
    type_identifier: BaseController
    class_body
      method_definition
        accessibility_modifier: protected
        property_identifier: handleSuccess
        type_parameters: <T>
        formal_parameters
          required_parameter (res: Response)
          required_parameter (data: T)
        return_type: Response
        statement_block
```

**Key Nodes**:
- `abstract_class_declaration` - Identifies abstract classes
- `accessibility_modifier` - TypeScript access modifiers (protected/private/public)
- `type_parameters` - Generic type parameters (`<T>`)
- `generic_type` - Generic type annotations (`ApiResponse<T>`)

### Method Chaining Pattern

```typescript
return res.status(statusCode).json(response);
```

**AST Pattern**:
```
call_expression
  function: member_expression
    object: call_expression           // Inner: res.status(200)
      function: member_expression
        object: identifier (res)
        property: property_identifier (status)
      arguments: identifier (statusCode)
    property: property_identifier (json)
  arguments: identifier (response)
```

## Required Dependencies

### Type Definitions

```typescript
// @/utils/response.ts
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  timestamp: string;
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
    totalPages?: number;
    hasNextPage?: boolean;
    hasPrevPage?: boolean;
  };
}

export interface ApiError {
  success: false;
  message: string;
  error: string;
  timestamp: string;
  details?: Record<string, string>;
  stack?: string;
}
```

### Error Classes

```typescript
// @/utils/errors.ts
export class AppError extends Error {
  constructor(
    public message: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}
```

## Best Practices

### 1. Always Extend BaseController

```typescript
// ✅ CORRECT
export class MyController extends BaseController { }

// ❌ WRONG - Don't implement response handling manually
export class MyController {
  async myMethod(req: Request, res: Response) {
    res.json({ data: 'something' }); // Inconsistent format!
  }
}
```

### 2. Use Try-Catch in All Async Methods

```typescript
// ✅ CORRECT
async myMethod(req: Request, res: Response): Promise<Response> {
  try {
    const result = await this.service.doWork();
    return this.handleSuccess(res, result);
  } catch (error) {
    return this.handleError(res, error as Error);
  }
}

// ❌ WRONG - No error handling
async myMethod(req: Request, res: Response): Promise<Response> {
  const result = await this.service.doWork(); // Unhandled promise rejection!
  return this.handleSuccess(res, result);
}
```

### 3. Use Descriptive Error Messages

```typescript
// ✅ CORRECT
return this.handleError(res, error as Error, 'Failed to create user account');

// ❌ WRONG - Generic message
return this.handleError(res, error as Error, 'Error');
```

### 4. Use Appropriate Status Codes

```typescript
// ✅ CORRECT
return this.handleSuccess(res, event, 'Event created', 201); // Created
return this.handleError(res, error as Error, 'Not found', 404); // Not Found

// ❌ WRONG - Always using 200
return this.handleSuccess(res, event, 'Event created', 200); // Should be 201
```

### 5. Handle Validation Errors Separately

```typescript
// ✅ CORRECT
try {
  const data = schema.parse(req.body);
  // ... use validated data
} catch (error) {
  if (error instanceof ZodError) {
    return this.handleValidationError(res, error);
  }
  return this.handleError(res, error as Error);
}

// ❌ WRONG - Generic error for validation
try {
  const data = schema.parse(req.body);
} catch (error) {
  return this.handleError(res, error as Error); // Loses validation details!
}
```

## Integration with Middleware

### Route Definition

```typescript
import { Router } from 'express';
import { AnalyticsController } from '@/controllers/AnalyticsController';
import { authenticate } from '@/middleware/authentication';
import { validateRequest } from '@/middleware/validation';

const router = Router();
const controller = new AnalyticsController(analyticsService);

// Protected route with validation
router.post(
  '/events/track',
  authenticate,                          // Auth middleware
  validateRequest(trackEventSchema),     // Validation middleware
  (req, res) => controller.trackEvent(req, res)  // Controller handler
);

// Public route
router.get(
  '/stats',
  (req, res) => controller.getStats(req, res)
);
```

## Benefits

1. **Consistency**: All API responses follow the same format
2. **Type Safety**: TypeScript generics ensure type-safe data handling
3. **Error Tracking**: Automatic Sentry integration for all errors
4. **Developer Experience**: Simple, predictable API for controllers
5. **Logging**: Centralized structured logging with context
6. **Maintainability**: Changes to response format happen in one place
7. **Testing**: Easy to mock and test controller responses

## Common Patterns

### Pattern: CRUD Controller

```typescript
export class ResourceController extends BaseController {
  async create(req: Request, res: Response): Promise<Response> {
    try {
      const resource = await this.service.create(req.body);
      return this.handleSuccess(res, resource, 'Resource created', 201);
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to create resource');
    }
  }

  async findAll(req: Request, res: Response): Promise<Response> {
    try {
      const { page = 1, limit = 10 } = req.query;
      const { items, total } = await this.service.findAll({ page, limit });
      return this.handlePaginatedResponse(res, items, page, limit, total);
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to retrieve resources');
    }
  }

  async findById(req: Request, res: Response): Promise<Response> {
    try {
      const resource = await this.service.findById(req.params.id);
      if (!resource) {
        throw new AppError('Resource not found', 404);
      }
      return this.handleSuccess(res, resource);
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to retrieve resource');
    }
  }

  async update(req: Request, res: Response): Promise<Response> {
    try {
      const resource = await this.service.update(req.params.id, req.body);
      return this.handleSuccess(res, resource, 'Resource updated');
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to update resource');
    }
  }

  async delete(req: Request, res: Response): Promise<Response> {
    try {
      await this.service.delete(req.params.id);
      return this.handleSuccess(res, null, 'Resource deleted', 204);
    } catch (error) {
      return this.handleError(res, error as Error, 'Failed to delete resource');
    }
  }
}
```

## Testing

### Unit Test Example

```typescript
import { Response } from 'express';
import { AnalyticsController } from './AnalyticsController';
import { AnalyticsService } from '@/services/AnalyticsService';

describe('AnalyticsController', () => {
  let controller: AnalyticsController;
  let mockService: jest.Mocked<AnalyticsService>;
  let mockResponse: Partial<Response>;

  beforeEach(() => {
    mockService = {
      trackEvent: jest.fn(),
    } as any;

    controller = new AnalyticsController(mockService);

    mockResponse = {
      status: jest.fn().mockReturnThis(),
      json: jest.fn().mockReturnThis(),
    };
  });

  it('should return success response on successful event tracking', async () => {
    const mockEvent = { id: 'evt_123', type: 'page_view' };
    mockService.trackEvent.mockResolvedValue(mockEvent);

    const mockRequest = { body: { type: 'page_view' } } as any;

    await controller.trackEvent(mockRequest, mockResponse as Response);

    expect(mockResponse.status).toHaveBeenCalledWith(201);
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({
        success: true,
        message: 'Event tracked successfully',
        data: mockEvent,
      })
    );
  });

  it('should return error response on failure', async () => {
    const mockError = new Error('Database error');
    mockService.trackEvent.mockRejectedValue(mockError);

    const mockRequest = { body: { type: 'page_view' } } as any;

    await controller.trackEvent(mockRequest, mockResponse as Response);

    expect(mockResponse.status).toHaveBeenCalledWith(500);
    expect(mockResponse.json).toHaveBeenCalledWith(
      expect.objectContaining({
        success: false,
        message: 'Failed to track event',
        error: 'Database error',
      })
    );
  });
});
```

## Related Patterns

- **Layered Architecture**: Controllers delegate to services
- **Dependency Injection**: Services injected into controllers
- **Repository Pattern**: Services use repositories for data access
- **Error Boundary Middleware**: Global error handler as last resort

## References

- AnalyticsBot backend: `/Users/alyshialedlie/code/ISPublicSites/AnalyticsBot/backend/src/controllers/BaseController.ts`
- Response types: `/Users/alyshialedlie/code/ISPublicSites/AnalyticsBot/backend/src/utils/response.ts`
- Error classes: `/Users/alyshialedlie/code/ISPublicSites/AnalyticsBot/backend/src/utils/errors.ts`
