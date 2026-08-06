from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.adapters.models import EnvironmentalFactorRecord, ProductRecord
from app.domain.product import EnvironmentalFactor, Product


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count_products(self) -> int:
        return self.session.scalar(select(func.count(ProductRecord.id))) or 0

    def find_product(self, product_id: str) -> Product | None:
        record = self.session.get(ProductRecord, product_id)
        return self._to_product(record) if record else None

    def find_by_barcode(self, barcode: str) -> Product | None:
        record = self.session.scalar(
            select(ProductRecord).where(ProductRecord.barcode == barcode)
        )
        return self._to_product(record) if record else None

    def search_products(self, query: str, limit: int = 30) -> list[Product]:
        normalized_query = query.strip().lower()
        statement = select(ProductRecord).order_by(ProductRecord.name).limit(limit)
        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    func.lower(ProductRecord.name).like(pattern),
                    func.lower(ProductRecord.brand).like(pattern),
                    ProductRecord.barcode.like(pattern),
                )
            )
        return [self._to_product(record) for record in self.session.scalars(statement)]

    def list_by_category(self, category: str) -> list[Product]:
        records = self.session.scalars(
            select(ProductRecord)
            .where(ProductRecord.category == category)
            .order_by(ProductRecord.id)
        )
        return [self._to_product(record) for record in records]

    def list_complete_products(self) -> list[Product]:
        records = self.session.scalars(
            select(ProductRecord)
            .where(
                ProductRecord.price_clp.is_not(None),
                ProductRecord.package_grams.is_not(None),
                ProductRecord.category != "other",
            )
            .order_by(ProductRecord.id)
        )
        return [self._to_product(record) for record in records]

    def save_product(self, product: Product) -> Product:
        record = self.session.get(ProductRecord, product.id)
        if record is None:
            record = ProductRecord(id=product.id)
            self.session.add(record)
        self._update_product_record(record, product)
        self.session.commit()
        self.session.refresh(record)
        return self._to_product(record)

    def find_environmental_factor(
        self,
        category: str,
    ) -> EnvironmentalFactor | None:
        record = self.session.get(EnvironmentalFactorRecord, category)
        return self._to_environmental_factor(record) if record else None

    def list_environmental_factors(self) -> list[EnvironmentalFactor]:
        records = self.session.scalars(
            select(EnvironmentalFactorRecord).order_by(
                EnvironmentalFactorRecord.category
            )
        )
        return [self._to_environmental_factor(record) for record in records]

    def save_environmental_factor(
        self,
        factor: EnvironmentalFactor,
    ) -> EnvironmentalFactor:
        record = self.session.get(EnvironmentalFactorRecord, factor.category)
        if record is None:
            record = EnvironmentalFactorRecord(category=factor.category)
            self.session.add(record)
        record.co2e_kg_per_kg = factor.co2e_kg_per_kg
        record.source = factor.source
        record.source_version = factor.source_version
        record.confidence = factor.confidence
        record.updated_at = factor.updated_at
        self.session.commit()
        self.session.refresh(record)
        return self._to_environmental_factor(record)

    @staticmethod
    def _update_product_record(record: ProductRecord, product: Product) -> None:
        record.barcode = product.barcode
        record.barcode_raw = product.barcode_raw
        record.name = product.name
        record.brand = product.brand
        record.category = product.category
        record.price_clp = product.price_clp
        record.package_grams = product.package_grams
        record.origin = product.origin
        record.packaging_type = product.packaging_type
        record.recyclable = product.recyclable
        record.certifications = list(product.certifications)
        record.social_indicator = product.social_indicator
        record.external_provider = product.external_provider
        record.external_id = product.external_id
        record.updated_at = product.updated_at

    @staticmethod
    def _to_product(record: ProductRecord) -> Product:
        return Product(
            id=record.id,
            barcode=record.barcode,
            barcode_raw=record.barcode_raw,
            name=record.name,
            brand=record.brand,
            category=record.category,
            price_clp=record.price_clp,
            package_grams=record.package_grams,
            origin=record.origin,
            packaging_type=record.packaging_type,
            recyclable=record.recyclable,
            certifications=tuple(record.certifications or []),
            social_indicator=record.social_indicator,
            external_provider=record.external_provider,
            external_id=record.external_id,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_environmental_factor(
        record: EnvironmentalFactorRecord,
    ) -> EnvironmentalFactor:
        return EnvironmentalFactor(
            category=record.category,
            co2e_kg_per_kg=record.co2e_kg_per_kg,
            source=record.source,
            source_version=record.source_version,
            confidence=record.confidence,
            updated_at=record.updated_at,
        )
