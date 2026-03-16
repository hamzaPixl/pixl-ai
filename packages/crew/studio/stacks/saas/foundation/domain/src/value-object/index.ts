import Decimal from 'decimal.js';

export abstract class ValueObject<TProps> {
  protected readonly props: TProps;

  constructor(props: TProps) {
    this.props = Object.freeze(props);
  }

  equals(other: ValueObject<TProps>): boolean {
    if (other === null || other === undefined) {
      return false;
    }
    return JSON.stringify(this.props) === JSON.stringify(other.props);
  }

  protected clone(newProps: Partial<TProps>): TProps {
    return { ...this.props, ...newProps };
  }
}

export interface MoneyProps {
  amount: number;
  currency: string;
}

export class Money extends ValueObject<MoneyProps> {
  private constructor(props: MoneyProps) {
    super(props);
  }

  static create(amount: number, currency: string): Money {
    if (amount < 0) {
      throw new Error('Amount cannot be negative');
    }
    // Normalize to 2 decimal places using Decimal for precision
    const normalized = new Decimal(amount).toDecimalPlaces(2).toNumber();
    return new Money({ amount: normalized, currency: currency.toUpperCase() });
  }

  static zero(currency: string): Money {
    return new Money({ amount: 0, currency: currency.toUpperCase() });
  }

  get amount(): number {
    return this.props.amount;
  }

  get currency(): string {
    return this.props.currency;
  }

  add(other: Money): Money {
    this.ensureSameCurrency(other);
    const result = new Decimal(this.amount).plus(other.amount).toNumber();
    return Money.create(result, this.currency);
  }

  subtract(other: Money): Money {
    this.ensureSameCurrency(other);
    const result = new Decimal(this.amount).minus(other.amount).toNumber();
    if (result < 0) {
      throw new Error('Result cannot be negative');
    }
    return Money.create(result, this.currency);
  }

  multiply(factor: number): Money {
    const result = new Decimal(this.amount).times(factor).toDecimalPlaces(2).toNumber();
    return Money.create(result, this.currency);
  }

  divide(divisor: number): Money {
    if (divisor === 0) {
      throw new Error('Cannot divide by zero');
    }
    const result = new Decimal(this.amount).dividedBy(divisor).toDecimalPlaces(2).toNumber();
    return Money.create(result, this.currency);
  }

  isZero(): boolean {
    return this.amount === 0;
  }

  isGreaterThan(other: Money): boolean {
    this.ensureSameCurrency(other);
    return new Decimal(this.amount).greaterThan(other.amount);
  }

  isLessThan(other: Money): boolean {
    this.ensureSameCurrency(other);
    return new Decimal(this.amount).lessThan(other.amount);
  }

  isGreaterThanOrEqual(other: Money): boolean {
    this.ensureSameCurrency(other);
    return new Decimal(this.amount).greaterThanOrEqualTo(other.amount);
  }

  isLessThanOrEqual(other: Money): boolean {
    this.ensureSameCurrency(other);
    return new Decimal(this.amount).lessThanOrEqualTo(other.amount);
  }

  private ensureSameCurrency(other: Money): void {
    if (this.currency !== other.currency) {
      throw new Error(`Currency mismatch: ${this.currency} vs ${other.currency}`);
    }
  }

  override toString(): string {
    return `${this.amount.toFixed(2)} ${this.currency}`;
  }
}

export interface AddressProps {
  street: string;
  city: string;
  postalCode: string;
  country: string;
  state?: string;
}

export class Address extends ValueObject<AddressProps> {
  private constructor(props: AddressProps) {
    super(props);
  }

  static create(props: AddressProps): Address {
    if (!props.street || !props.city || !props.postalCode || !props.country) {
      throw new Error('Address requires street, city, postal code, and country');
    }
    return new Address(props);
  }

  get street(): string {
    return this.props.street;
  }

  get city(): string {
    return this.props.city;
  }

  get postalCode(): string {
    return this.props.postalCode;
  }

  get country(): string {
    return this.props.country;
  }

  get state(): string | undefined {
    return this.props.state;
  }

  format(): string {
    const parts = [this.street, this.city, this.postalCode];
    if (this.state) {
      parts.push(this.state);
    }
    parts.push(this.country);
    return parts.join(', ');
  }
}

export class Email extends ValueObject<{ value: string }> {
  private static readonly EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  private constructor(value: string) {
    super({ value: value.toLowerCase() });
  }

  static create(value: string): Email {
    if (!Email.EMAIL_REGEX.test(value)) {
      throw new Error(`Invalid email: ${value}`);
    }
    return new Email(value);
  }

  get value(): string {
    return this.props.value;
  }

  get domain(): string {
    const parts = this.props.value.split('@');
    return parts[1] ?? '';
  }

  override toString(): string {
    return this.props.value;
  }
}
