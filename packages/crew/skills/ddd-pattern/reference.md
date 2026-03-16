# Tactical DDD Patterns

## Entity

An Entity has a **unique identity** that persists over time. Two entities with identical fields but different IDs are different objects.

```python
from uuid import UUID, uuid4

class EntityId:
    """Strongly-typed entity identifier base class."""
    def __init__(self, value: UUID | None = None):
        self._value = value or uuid4()

    @property
    def value(self) -> UUID:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

class OrderId(EntityId):
    pass

class Order:
    """Entity with identity, lifecycle, and behavior."""
    def __init__(self, id: OrderId, customer_id: CustomerId, status: str = "draft"):
        self._id = id
        self._customer_id = customer_id
        self._status = status
        self._line_items: list["LineItem"] = []

    @property
    def id(self) -> OrderId:
        return self._id

    def cancel(self) -> None:
        if self._status == "shipped":
            raise DomainError("Cannot cancel a shipped order")
        self._status = "cancelled"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Order) and self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)
```

## Value Object

Defined entirely by its attributes. **No identity**, always **immutable**. Two value objects with the same values are equal.

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    """Immutable value object. Equality is by value. Validation in __post_init__."""
    amount: Decimal
    currency: str

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.currency not in ("USD", "EUR", "GBP"):
            raise ValueError(f"Unsupported currency: {self.currency}")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise DomainError(f"Cannot operate on {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise DomainError(f"Cannot operate on {self.currency} and {other.currency}")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def multiply(self, factor: int) -> "Money":
        return Money(amount=self.amount * factor, currency=self.currency)

    @staticmethod
    def zero(currency: str = "USD") -> "Money":
        return Money(amount=Decimal("0"), currency=currency)
```

## Aggregate

A cluster of entities and value objects with a single **Aggregate Root** as entry point. Defines a **consistency boundary**.

### Rules

1. Root has globally unique identity; external objects reference only the root.
2. All modifications go through the root; invariants always consistent.
3. Cross-aggregate invariants are eventually consistent. Keep aggregates small.

```python
class Order:
    """Aggregate root. All access to LineItems goes through Order."""

    def __init__(self, id: OrderId, customer_id: CustomerId):
        self._id = id
        self._customer_id = customer_id
        self._status = OrderStatus.DRAFT
        self._line_items: list[LineItem] = []
        self._events: list[DomainEvent] = []

    def add_line_item(self, product_id: ProductId, quantity: int, unit_price: Money) -> None:
        if self._status != OrderStatus.DRAFT:
            raise DomainError("Cannot modify a non-draft order")
        if quantity <= 0:
            raise DomainError("Quantity must be positive")
        self._line_items.append(LineItem(
            id=LineItemId.generate(), product_id=product_id,
            quantity=quantity, unit_price=unit_price,
        ))

    def submit(self) -> None:
        if not self._line_items:
            raise DomainError("Cannot submit an order with no line items")
        self._status = OrderStatus.SUBMITTED
        self._events.append(OrderSubmitted(order_id=self._id.value))

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events


class LineItem:
    """Child entity within Order aggregate. No global identity."""
    def __init__(self, id: LineItemId, product_id: ProductId, quantity: int, unit_price: Money):
        self._id, self._product_id = id, product_id
        self._quantity, self._unit_price = quantity, unit_price

    @property
    def subtotal(self) -> Money:
        return self._unit_price.multiply(self._quantity)
```

## Repository

Interface in **domain layer**; implementation in **infrastructure layer**. One repo per aggregate root, returns domain objects, no business logic.

```python
# domain/ordering/repositories.py (interface)
from abc import ABC, abstractmethod

class OrderRepository(ABC):
    @abstractmethod
    async def find_by_id(self, order_id: OrderId) -> Order | None: ...
    @abstractmethod
    async def save(self, order: Order) -> None: ...
    @abstractmethod
    async def delete(self, order_id: OrderId) -> None: ...


# infrastructure/ordering/sql_order_repository.py (implementation)
class SqlOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_id(self, order_id: OrderId) -> Order | None:
        stmt = select(OrderORM).where(OrderORM.id == order_id.value).options(selectinload(OrderORM.line_items))
        result = await self._session.execute(stmt)
        orm_obj = result.scalar_one_or_none()
        return OrderMapper.to_domain(orm_obj) if orm_obj else None

    async def save(self, order: Order) -> None:
        orm_obj = OrderMapper.to_orm(order)
        await self._session.merge(orm_obj)
        await self._session.flush()
```

## Domain Service

Encapsulates business logic that does not belong to a single entity or value object.

```python
# domain/ordering/services/pricing_service.py
class PricingService:
    """Domain service: pricing spans Order and discount rules."""

    def calculate_discounted_total(self, order: Order, discount_percentage: Decimal) -> Money:
        if discount_percentage < 0 or discount_percentage > 100:
            raise DomainError("Discount must be between 0 and 100")
        total = order.total
        discount = total.multiply_decimal(discount_percentage / Decimal("100"))
        return total.subtract(discount)
```

## DomainError

```python
class DomainError(Exception):
    """Raised when a domain invariant or business rule is violated."""
    pass
```
# Strategic DDD Patterns

Strategic patterns define how bounded contexts relate to each other and how teams organize around domain boundaries.

## Bounded Context

A boundary within which a particular domain model is defined and applicable. The same real-world concept may have different representations in different contexts.

### Key Principles

- Each bounded context has its own Ubiquitous Language.
- A model is only valid within its bounded context.
- Same concept, different models in different contexts (e.g., `User` in identity vs. `Customer` in ordering).
- Bounded contexts align with team boundaries (Conway's Law).

### Identifying Bounded Contexts

1. **Language clues**: Same word means different things to different people = context boundary.
2. **Transaction boundaries**: Objects that must be consistent together belong in the same context.
3. **Team boundaries**: Each team owns one or more bounded contexts.
4. **Change frequency**: Objects that change together belong together.

### Python Bounded Context Structure

```python
# ordering/                        <-- bounded context
#   domain/
#     entities/order.py, line_item.py
#     value_objects/money.py, order_status.py, order_id.py
#     repositories.py              <-- interfaces only
#     services/pricing_service.py
#     events/order_submitted.py
#   application/submit_order.py, cancel_order.py
#   infrastructure/sql_order_repository.py, orm_models.py, mappers.py
# Each context is self-contained. No direct imports across context boundaries.
```

## Context Map

Documents relationships between bounded contexts.

### Relationship Types

| Relationship | Description |
|---|---|
| **Shared Kernel** | Two contexts share a small subset of domain model. Changes require coordination. |
| **Customer-Supplier** | Supplier provides data the customer depends on. Supplier defines the contract. |
| **Conformist** | Downstream conforms to upstream's model. No translation layer. |
| **Anti-Corruption Layer** | Downstream translates upstream model into its own language. Protects from external model pollution. |
| **Published Language** | Contexts communicate using a well-defined shared schema (JSON, Protobuf, OpenAPI). |
| **Open Host Service** | A context provides a well-defined API for multiple consumers. |
| **Separate Ways** | Contexts have no relationship and do not communicate. |

## Ubiquitous Language

Shared vocabulary between developers and domain experts within a bounded context.

### Example Glossary

| Term | Definition |
|------|-----------|
| Order | A customer's request to purchase one or more products |
| Line Item | A single product entry within an order, with quantity and price |
| Submit | The act of finalizing a draft order for processing |
| Cancel | Voiding an order before it has been shipped |
| Draft | An order being assembled, not yet submitted |

```python
# Good: uses domain language
class Order:
    def submit(self) -> None: ...
    def cancel(self) -> None: ...
    def add_line_item(self, ...) -> None: ...

# Bad: uses technical or generic language
class OrderEntity:
    def process(self) -> None: ...      # "process" is vague
    def set_status(self, s: str): ...    # exposes implementation
```

## Anti-Corruption Layer (ACL)

Protects your domain model from external models (legacy systems, third-party APIs, other bounded contexts). Sits in the infrastructure layer.

```python
# 1. Define what the domain needs (domain layer port)
class ShippingCostCalculator(ABC):
    @abstractmethod
    async def calculate(self, destination: Address, weight_kg: Decimal) -> Money: ...


# 2. Implement the adapter (infrastructure layer)
class FedExShippingAdapter(ShippingCostCalculator):
    """Translates FedEx API into domain terms."""

    def __init__(self, fedex_client: FedExApiClient):
        self._client = fedex_client

    async def calculate(self, destination: Address, weight_kg: Decimal) -> Money:
        fedex_request = {
            "dest_postal": destination.zip_code,
            "dest_country_iso": destination.country,
            "weight_lbs": float(weight_kg * Decimal("2.20462")),
            "service_type": "GROUND",
        }
        fedex_response = await self._client.get_rate(fedex_request)
        return Money(amount=Decimal(str(fedex_response["total_charge"])), currency="USD")
```

### ACL at Context Boundaries

```python
# billing context receives OrderSubmitted event from ordering context
class OrderingEventTranslator:
    """ACL: translates ordering events into billing domain objects."""

    def translate_order_submitted(self, event: dict) -> InvoiceCreationRequest:
        return InvoiceCreationRequest(
            reference_id=ReferenceId(event["order_id"]),
            customer_id=BillingCustomerId(event["customer_id"]),
            total=Money(
                amount=Decimal(str(event["total_amount_cents"])) / 100,
                currency=event["currency"],
            ),
        )
```
# Domain Event Patterns

Domain events represent something that happened in the domain. Used for communication between aggregates and bounded contexts.

## Naming Conventions

- Always past tense: `OrderSubmitted`, `PaymentReceived`, `InventoryReserved`.
- Include the aggregate name: `OrderSubmitted`, not `Submitted`.
- Be specific: `OrderShippingAddressChanged`, not `OrderUpdated`.

## Event Structure

Every domain event includes: unique event ID, timestamp, aggregate ID, and payload.

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events. Immutable."""
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OrderSubmitted(DomainEvent):
    order_id: UUID = field(default=None)
    customer_id: UUID = field(default=None)
    total_amount_cents: int = field(default=0)
    currency: str = field(default="USD")
    line_item_count: int = field(default=0)


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    order_id: UUID = field(default=None)
    reason: str = field(default="")


@dataclass(frozen=True)
class PaymentReceived(DomainEvent):
    payment_id: UUID = field(default=None)
    order_id: UUID = field(default=None)
    amount_cents: int = field(default=0)
    method: str = field(default="")
```

## Collecting Events from Aggregates

Aggregates collect events during mutations; application layer publishes after saving.

```python
class Order:
    def __init__(self, id: OrderId, customer_id: CustomerId):
        self._id = id
        self._customer_id = customer_id
        self._status = OrderStatus.DRAFT
        self._line_items: list[LineItem] = []
        self._events: list[DomainEvent] = []

    def submit(self) -> None:
        if not self._line_items:
            raise DomainError("Cannot submit empty order")
        self._status = OrderStatus.SUBMITTED
        self._events.append(OrderSubmitted(
            order_id=self._id.value, customer_id=self._customer_id.value,
            total_amount_cents=int(self.total.amount * 100),
            currency=self.total.currency, line_item_count=len(self._line_items),
        ))

    def collect_events(self) -> list[DomainEvent]:
        """Application layer calls this after saving to get events for publishing."""
        events = list(self._events)
        self._events.clear()
        return events
```

## Event Bus (In-Process)

In-process event bus for publishing and subscribing within a single service.

```python
# domain/shared/event_bus.py (interface)
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Type

EventHandler = Callable[[DomainEvent], Awaitable[None]]

class EventBus(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...
    @abstractmethod
    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None: ...


# infrastructure/shared/in_memory_event_bus.py (implementation)
from collections import defaultdict

class InMemoryEventBus(EventBus):
    def __init__(self):
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            await handler(event)

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
```

## Event Handler

Event handlers are application-layer components that react to domain events in the consuming bounded context.

```python
# application/billing/handlers/on_order_submitted.py
class OnOrderSubmitted:
    """Creates an invoice when an order is submitted."""

    def __init__(self, invoice_repo: InvoiceRepository):
        self._invoice_repo = invoice_repo

    async def __call__(self, event: OrderSubmitted) -> None:
        invoice = Invoice(
            id=InvoiceId.generate(), order_id=event.order_id,
            customer_id=event.customer_id,
            amount_cents=event.total_amount_cents, currency=event.currency,
        )
        await self._invoice_repo.save(invoice)
```

## Publishing Pattern: Collect-Then-Publish

Collect events during aggregate mutations, save the aggregate, then publish. Ensures events are only published after state change is persisted.

```python
class SubmitOrderUseCase:
    def __init__(self, order_repo: OrderRepository, event_bus: EventBus):
        self._order_repo = order_repo
        self._event_bus = event_bus

    async def execute(self, order_id: OrderId) -> None:
        order = await self._order_repo.find_by_id(order_id)
        if not order:
            raise NotFoundError(f"Order {order_id} not found")

        order.submit()                                  # 1. Mutate aggregate (collects events)
        await self._order_repo.save(order)              # 2. Save aggregate
        for event in order.collect_events():            # 3. Publish events
            await self._event_bus.publish(event)
```

## Wiring Events at Startup

```python
# main.py or container.py
def configure_event_bus(invoice_repo, reservation_service) -> EventBus:
    bus = InMemoryEventBus()
    bus.subscribe(OrderSubmitted, OnOrderSubmitted(invoice_repo))
    bus.subscribe(OrderSubmitted, OnOrderSubmittedReserveInventory(reservation_service))
    return bus
```
# Layer Architecture for DDD

Core principle: **Dependency Rule** -- source code dependencies always point inward, from infrastructure toward the domain.

## The Three Layers

```
+--------------------------------------------------+
|  Infrastructure (outermost)                       |
|  - DB repos impl, HTTP routes, external APIs      |
|  - Message brokers, file system, email            |
+--------------------------------------------------+
|  Application (middle)                             |
|  - Use cases / application services               |
|  - DTOs, Event handlers, Transaction management   |
+--------------------------------------------------+
|  Domain (innermost)                               |
|  - Entities, Value objects, Aggregates            |
|  - Repository interfaces (ports)                  |
|  - Domain services, events, errors                |
+--------------------------------------------------+
```

### Dependency Rule

- **Domain** depends on nothing. Zero external imports. Only standard library.
- **Application** depends on Domain. Orchestrates domain objects through interfaces.
- **Infrastructure** depends on Domain (implements interfaces) and Application (wires use cases).
- **Never**: Domain imports from Application or Infrastructure.
- **Never**: Application imports from Infrastructure (use dependency injection).

## Directory Structure (Python)

```
src/
  ordering/                          # Bounded context
    domain/
      entities/
        order.py                     # Aggregate root
        line_item.py                 # Child entity
      value_objects/
        order_id.py
        money.py
        order_status.py
      repositories.py               # Abstract base classes (ports)
      services/
        pricing_service.py           # Domain service
      events/
        order_submitted.py
      errors.py                      # DomainError
    application/
      submit_order.py                # Use case
      cancel_order.py
      dto.py
    infrastructure/
      sql_order_repository.py        # Repository implementation
      orm_models.py
      mappers.py
  shared/                            # Shared kernel
    domain/
      events.py                      # Base DomainEvent class
      event_bus.py                   # EventBus interface
      errors.py
    infrastructure/
      in_memory_event_bus.py
```

## Domain Layer (Innermost)

Pure business logic. No knowledge of databases, HTTP, or any framework.

```python
# ordering/domain/entities/order.py
# ZERO external imports. Only standard library and domain modules.
from ordering.domain.value_objects.order_id import OrderId
from ordering.domain.value_objects.money import Money
from ordering.domain.value_objects.order_status import OrderStatus
from ordering.domain.errors import DomainError

class Order:
    def __init__(self, id: OrderId, customer_id: CustomerId):
        self._id = id
        self._customer_id = customer_id
        self._status = OrderStatus.DRAFT
        self._line_items: list[LineItem] = []

    def submit(self) -> None:
        if not self._line_items:
            raise DomainError("Cannot submit order with no line items")
        self._status = OrderStatus.SUBMITTED
```

## Application Layer (Middle)

Orchestrates domain objects to fulfill use cases. Loads aggregates, calls domain methods, saves results, publishes events.

```python
# ordering/application/submit_order.py
class SubmitOrderUseCase:
    """Orchestrates domain objects -- does NOT contain business logic."""

    def __init__(self, order_repo: OrderRepository, event_bus: EventBus):
        self._order_repo = order_repo
        self._event_bus = event_bus

    async def execute(self, order_id: str) -> dict:
        order = await self._order_repo.find_by_id(OrderId(order_id))
        if not order:
            raise NotFoundError(f"Order {order_id} not found")

        order.submit()                                    # Domain logic inside aggregate
        await self._order_repo.save(order)

        for event in order.collect_events():
            await self._event_bus.publish(event)

        return {"order_id": str(order.id.value), "status": order.status.value}
```

## Infrastructure Layer (Outermost)

Concrete implementations for domain interfaces. Handles all I/O.

### Mapper Example

```python
# ordering/infrastructure/mappers.py
class OrderMapper:
    """Translates between domain Order and ORM OrderORM."""

    @staticmethod
    def to_domain(orm: OrderORM) -> Order:
        order = Order(id=OrderId(orm.id), customer_id=CustomerId(orm.customer_id))
        order._status = OrderStatus(orm.status)
        order._line_items = [
            LineItem(id=LineItemId(item.id), product_id=ProductId(item.product_id),
                     quantity=item.quantity,
                     unit_price=Money(amount=item.unit_price_amount, currency=item.unit_price_currency))
            for item in orm.line_items
        ]
        return order

    @staticmethod
    def to_orm(order: Order) -> OrderORM:
        return OrderORM(
            id=order.id.value, customer_id=order.customer_id.value, status=order.status.value,
            line_items=[
                LineItemORM(id=item.id.value, product_id=item.product_id.value,
                            quantity=item.quantity, unit_price_amount=item.unit_price.amount,
                            unit_price_currency=item.unit_price.currency)
                for item in order.line_items
            ],
        )
```

### HTTP Controller Example

```python
# ordering/infrastructure/routes.py
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

@router.post("/{order_id}/submit", status_code=status.HTTP_200_OK)
async def submit_order(order_id: str, use_case: SubmitOrderUseCase = Depends(get_submit_order_use_case)):
    try:
        return await use_case.execute(order_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except DomainError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

### Composition Root

```python
def create_app():
    db_session = create_async_session()
    event_bus = InMemoryEventBus()
    order_repo: OrderRepository = SqlOrderRepository(db_session)
    submit_order = SubmitOrderUseCase(order_repo=order_repo, event_bus=event_bus)
    app = FastAPI()
    app.include_router(create_order_routes(submit_order))
    return app
```

## Common Mistakes

```python
# BAD: domain imports SQLAlchemy    | GOOD: pure Python domain entity
from sqlalchemy import Column       | class Order:
class Order(Base): ...              |     def __init__(self, id: OrderId): ...

# BAD: business rule in controller  | GOOD: delegate to use case
if len(order.line_items) == 0:      | result = await use_case.execute(id)
    raise HTTPException(422, "...")  |

# BAD: repo returns ORM model       | GOOD: returns domain entity
def find(self, id) -> OrderORM: ... | def find(self, id) -> Order: ...
```
